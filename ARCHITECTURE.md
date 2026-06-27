# ARCHITECTURE.md — Sentinel Financial Ecosystem

> **Document Type:** Software Design Document (SDD)  
> **Version:** 1.0  
> **Author:** Lawrence 
> **Status:** Production  

---

## Table of Contents

1. [Project Vision](#1-project-vision)
2. [Business Problem](#2-business-problem)
3. [Requirements](#3-requirements)
4. [System Overview](#4-system-overview)
5. [Architecture Diagram](#5-architecture-diagram)
6. [Component Responsibilities](#6-component-responsibilities)
7. [Request Lifecycle](#7-request-lifecycle)
8. [Security Model](#8-security-model)
9. [Caching Strategy](#9-caching-strategy)
10. [Async Processing](#10-async-processing)
11. [Fraud Detection](#11-fraud-detection)
12. [Monitoring & Observability](#12-monitoring--observability)
13. [Testing Strategy](#13-testing-strategy)
14. [Deployment](#14-deployment)
15. [Scaling Strategy](#15-scaling-strategy)
16. [Trade-offs & Engineering Decisions](#16-trade-offs--engineering-decisions)
17. [Future Improvements](#17-future-improvements)

---

## 1. Project Vision

Sentinel Financial Ecosystem is a production-grade distributed backend for digital wallet operations. It is engineered to handle high-throughput peer-to-peer fund transfers with bank-grade integrity guarantees, real-time fraud scoring, asynchronous task processing, and full-stack observability.

The system is designed to answer one engineering question:

> **How do you build a financial backend that is simultaneously fast, safe, and observable — without compromising any of the three?**

The answer is a microservices architecture where each concern is isolated, every failure is handled explicitly, and every transaction is traceable from ingress to ledger commit.

---

## 2. Business Problem

Digital wallet systems face a specific class of failure that standard web applications do not:

**Race Conditions on Balance Mutations**  
When two transfers deduct from the same wallet simultaneously, naive implementations produce inconsistent balances. A wallet with $100 can be debited twice if both reads happen before either write commits.

**Duplicate Transactions**  
Network retries from mobile clients, load balancers, or payment gateways can trigger the same transaction multiple times. Without idempotency enforcement, users lose money to duplicate debits.

**Fraud at Scale**  
Every transfer carries fraud risk. Blocking the API response thread on a synchronous fraud check is unacceptable at scale — but skipping the check entirely creates risk exposure.

**Observability Gaps**  
Financial systems require complete audit trails. Without correlation IDs, distributed tracing, and structured logging, debugging a failed transaction across multiple services is impossible.

Sentinel is designed to solve all four problems simultaneously.

---

## 3. Requirements

### Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-01 | Users can register, login, and receive JWT tokens |
| FR-02 | Users can deposit and withdraw funds from their wallet |
| FR-03 | Users can transfer funds to other users by email |
| FR-04 | Every transfer is scored for fraud risk before execution |
| FR-05 | Transaction history is queryable by type and date |
| FR-06 | Post-transfer notifications are delivered asynchronously |

### Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-01 | Concurrent transfers to the same wallet must not corrupt balances |
| NFR-02 | Duplicate requests must be idempotent — no double-deductions |
| NFR-03 | The API must remain available if the fraud service is offline |
| NFR-04 | Every request must be traceable via a correlation ID |
| NFR-05 | All endpoints must be rate-limited per authenticated user |
| NFR-06 | The system must expose metrics for Prometheus scraping |

---

## 4. System Overview

Sentinel is composed of seven containerized services orchestrated by Docker Compose:

```
wallet-service      → Core API (FastAPI)
fraud-detector      → ML risk scoring microservice (FastAPI + Scikit-Learn)
celery-worker       → Asynchronous background task processor (Celery)
db                  → Relational ledger database (PostgreSQL 15)
redis               → Cache, idempotency store, and Celery broker (Redis 7)
prometheus          → Metrics collection
grafana             → Dashboard visualization
```

All services communicate over an isolated Docker bridge network. No service is directly reachable from the public internet except through the wallet-service on port 8000.

---

## 5. Architecture Diagram

```
                         ┌─────────────────────────────────────────────────┐
                         │          Docker Compose Network Boundary         │
                         │                                                   │
  ┌──────────┐           │  ┌─────────────────────────────────────────────┐ │
  │  Client  │──HTTPS───▶│  │           wallet-service (FastAPI)          │ │
  │ /Postman │           │  │                  Port 8000                  │ │
  └──────────┘           │  │                                             │ │
                         │  │  ┌──────────────┐   ┌────────────────────┐ │ │
                         │  │  │ JWT Auth     │   │ Idempotency        │ │ │
                         │  │  │ Engine       │   │ Middleware         │ │ │
                         │  │  │ (Bcrypt/HS256│   │ (Redis-backed)     │ │ │
                         │  │  └──────────────┘   └────────────────────┘ │ │
                         │  │                                             │ │
                         │  │  ┌──────────────┐   ┌────────────────────┐ │ │
                         │  │  │ Rate Limiter │   │ OpenTelemetry      │ │ │
                         │  │  │ (Redis       │   │ Tracing            │ │ │
                         │  │  │  Counter)    │   │ (Correlation IDs)  │ │ │
                         │  │  └──────────────┘   └────────────────────┘ │ │
                         │  └──────────────┬──────────────────────────────┘ │
                         │                 │                                  │
          ┌──────────────┼─────────────────┼──────────────────────┐          │
          │              │                 │                        │          │
          ▼              ▼                 ▼                        ▼          │
  ┌──────────────┐ ┌──────────┐  ┌───────────────┐  ┌────────────────────┐  │
  │ PostgreSQL 15│ │ Redis 7  │  │ fraud-detector│  │  celery-worker     │  │
  │ Port 5432    │ │ Port 6379│  │ Port 8001     │  │  (Notification     │  │
  │              │ │          │  │               │  │   Tasks)           │  │
  │ Ledger DB    │ │ Cache +  │  │ FastAPI +     │  │                    │  │
  │ Row Locking  │ │ Broker + │  │ Scikit-Learn  │  │ Consumes from      │  │
  │ ACID         │ │ Rate     │  │ ML Model      │  │ Redis Queue        │  │
  │ Transactions │ │ Limiting │  │               │  │                    │  │
  └──────────────┘ └──────────┘  └───────────────┘  └────────────────────┘  │
                                                                              │
          ┌───────────────────────────────────────────┐                       │
          │         Observability Stack               │                       │
          │                                           │                       │
          │  Prometheus (Port 9090) ──scrapes──▶ /metrics                    │
          │       │                                   │                       │
          │       ▼                                   │                       │
          │  Grafana (Port 3000)                      │                       │
          │  OpenTelemetry ──traces──▶ Tempo          │                       │
          └───────────────────────────────────────────┘                       │
                         │                                                     │
                         └─────────────────────────────────────────────────────┘
```

---

## 6. Component Responsibilities

### wallet-service (FastAPI)
The central API gateway and business logic layer. Responsible for:
- User registration and JWT issuance
- Wallet balance management (deposit, withdraw)
- Transfer orchestration — coordinating fraud check, DB write, and task dispatch
- Idempotency enforcement via middleware
- Rate limiting via Redis counters
- Prometheus metrics exposure at `/metrics`
- Distributed tracing via OpenTelemetry

### fraud-detector (FastAPI + Scikit-Learn)
An isolated microservice responsible exclusively for risk scoring. It:
- Accepts `{user_id, amount}` payloads
- Runs inference against a pre-trained Scikit-Learn model
- Returns `{risk_score: float, decision: "allow" | "block"}`
- Has no database access — stateless by design

Isolation rationale: fraud model updates, retraining, and scaling are decoupled from the core API. The fraud service can be replaced with a different model or vendor without touching wallet logic.

### celery-worker (Celery)
Consumes jobs from the Redis queue and executes background tasks:
- `send_transfer_notification` — simulates email/push delivery
- Runs in a prefork worker pool (8 concurrent processes)
- Retries failed tasks automatically

### PostgreSQL 15
The system of record for all financial data:
- `users` table — identity and credentials
- `wallets` table — balance ledger
- `transactions` table — immutable double-entry records

Row-level locking (`SELECT FOR UPDATE`) prevents concurrent balance corruption. All transfers use savepoints (`begin_nested`) for sub-transaction atomicity.

### Redis 7
Redis serves three distinct roles in this system:

| Role | Key Pattern | TTL |
|------|-------------|-----|
| Idempotency cache | `idempotency:{key}` | 24 hours |
| Rate limiter counter | `rate_limit:{user_id}` | 60 seconds |
| Celery message broker | Celery internal queues | Until consumed |

### Prometheus + Grafana
Prometheus scrapes `/metrics` every 15 seconds. Custom counters track:
- `transaction_count` — labelled by status (success/failed)
- `transaction_latency` — histogram of transfer durations

Grafana provides live dashboard visualization of all scraped metrics.

---

## 7. Request Lifecycle

### Transfer Request — Full Path

```
1. Client sends POST /wallets/wallet/transfer
   Headers: Authorization: Bearer <JWT>
   Body: { receiver_email, amount }

2. IdempotencyMiddleware checks Redis for duplicate key
   → If found: return cached response immediately
   → If not found: continue

3. JWT auth dependency verifies token signature
   → Decodes email from payload
   → Queries DB for user object

4. Rate limiter checks Redis counter for user_id
   → If count >= 5: return 429 Too Many Requests
   → If under limit: increment counter, continue

5. transaction_service.process_transfer() called:

   5a. Receiver lookup — DB query for receiver user
       → If not found: raise 404

   5b. Fraud check — POST to fraud-detector:8001/predict
       → Retry up to 3 times with 1s delay
       → If blocked: raise 403
       → If service unreachable: FAIL OPEN (log + allow)
       → If contract mismatch: FAIL OPEN (log + allow)

   5c. Pessimistic lock acquisition:
       → Lock wallet with lower ID first
       → Lock wallet with higher ID second
       → (Deterministic order prevents deadlocks)

   5d. Balance validation:
       → If sender.balance < amount: raise 400

   5e. Atomic balance swap:
       → sender.balance -= amount
       → receiver.balance += amount
       → Two Transaction records written (debit + credit)
       → db.commit()

   5f. Celery task enqueued:
       → send_transfer_notification.delay(...)
       → Returns immediately — does not block response

6. Response returned to client:
   { message: "Transfer successful", new_balance: float }

7. Celery worker picks up notification job
   → Executes in background (5s simulated delay)
   → Logs success
```

---

## 8. Security Model

### Authentication
- Stateless JWT tokens signed with HS256
- Tokens expire after 60 minutes (configurable)
- Passwords hashed with Bcrypt (adaptive cost factor)
- No plaintext credentials stored anywhere

### Authorization
- All wallet endpoints require valid JWT
- Users can only access their own wallet — enforced by extracting identity from the token, not from request parameters
- No admin bypass routes exist in production

### Rate Limiting
- Per-user sliding window: 5 requests per 60 seconds on transfer endpoint
- Implemented via Redis atomic increment (`INCR`) + expiry (`EX`)
- Returns `429 Too Many Requests` with human-readable message

### Idempotency
- Clients send `Idempotency-Key` header on mutating requests
- First response is cached in Redis for 24 hours
- Duplicate requests return the cached response without re-executing

### Fraud Detection
- Every transfer is scored before DB write
- Fraud service timeout: 3 seconds per attempt, 3 attempts maximum
- Fail-open strategy: availability prioritized over fraud prevention when service is unreachable (logged for audit)

### Request Tracing
- Every request receives a unique correlation ID (`X-Request-ID`)
- Propagated through all service calls
- Included in all log entries for full cross-service traceability

---

## 9. Caching Strategy

Redis is used for three caching patterns:

**Idempotency Cache (Write-Once)**  
Key: `idempotency:{client_key}`  
Value: Serialized HTTP response  
TTL: 24 hours  
Purpose: Prevent duplicate transaction execution on network retries

**Rate Limit Counter (Increment)**  
Key: `rate_limit:{user_id}`  
Value: Integer request count  
TTL: 60 seconds (sliding window)  
Purpose: Throttle high-frequency transfer attempts per user

**Celery Task Queue (Message Broker)**  
Redis acts as the message broker for Celery's distributed task queue. Tasks are serialized as JSON and consumed by worker processes in FIFO order.

No application-level query caching is implemented. Database queries are fast due to indexed foreign keys and targeted row-level locking — caching query results would add staleness risk without meaningful performance benefit at current scale.

---

## 10. Async Processing

### Why Celery + Redis Instead of Inline Processing

Post-transfer operations (notifications, audit events, analytics) are secondary to the transfer itself. Blocking the HTTP response thread on a 5-second email delivery is unacceptable — it degrades user experience and reduces API throughput.

Celery decouples these operations:

```
Transfer commits to DB
         │
         ├──▶ HTTP response returned to user (immediate)
         │
         └──▶ Notification job enqueued to Redis
                        │
                        ▼
              Celery worker picks up job
                        │
                        ▼
              Notification delivered (background)
```

The user receives their response in milliseconds. The notification executes asynchronously without affecting API latency.

### Task Configuration
- Serializer: JSON (human-readable, debuggable)
- Broker retry on startup: enabled
- Worker concurrency: 8 (prefork)
- Task acknowledgement: after execution (at-least-once delivery)

---

## 11. Fraud Detection

### Architecture Decision: Separate Microservice

The fraud detector is deployed as an independent FastAPI service rather than a library imported into the wallet service. Reasons:

1. **Independent scaling** — fraud scoring is CPU-intensive (ML inference). It can be scaled horizontally without scaling the API tier.
2. **Model independence** — the ML model can be retrained and redeployed without touching wallet code.
3. **Vendor substitution** — the fraud service can be replaced with a third-party provider (Stripe Radar, Sift) by changing one URL.

### Fail-Open Strategy

When the fraud service is unavailable, Sentinel **allows the transaction** rather than blocking it. This is a deliberate architectural decision:

**Reasoning:**
- Wallet availability is more valuable than fraud prevention availability
- A broken fraud service should not prevent legitimate users from accessing their money
- Every fail-open event is logged with the reason code for audit and alerting
- Monitoring alerts on elevated fail-open rates indicate fraud service degradation

**Fail-open triggers:**
| Trigger | Reason Code |
|---------|-------------|
| Connection refused / timeout | `fail_open_service_unreachable` |
| Response missing required fields | `fail_open_contract_mismatch` |
| Retry loop exhausted | `fail_open_loop_exhausted` |

**Alternative considered:** Fail-closed (block all transfers when fraud service is down). Rejected because a fraud service outage becomes a complete wallet outage — unacceptable for a financial product.

---

## 12. Monitoring & Observability

### Three Pillars

**Metrics (Prometheus + Grafana)**  
Custom Prometheus counters track transaction volume and status:
```python
TRANSACTION_COUNT = Counter('transaction_count', 'Total transactions', ['status'])
TRANSACTION_LATENCY = Histogram('transaction_latency_seconds', 'Transfer duration')
```
Prometheus scrapes `/metrics` every 15 seconds. Grafana renders live dashboards.

**Traces (OpenTelemetry)**  
Every request is instrumented with OpenTelemetry spans. Traces export to Tempo via gRPC on port 4317. If Tempo is unavailable, tracing degrades gracefully to a no-op — the API continues operating normally.

**Logs (Structured + Correlation IDs)**  
All log entries include:
- Timestamp
- Log level
- Correlation ID (`X-Request-ID`)
- Service name
- Event description

This makes cross-service debugging deterministic — a single correlation ID traces a transfer from API ingress through fraud check to DB commit to Celery notification.

---

## 13. Testing Strategy

### Test Architecture

Tests use SQLite in-memory databases as drop-in replacements for PostgreSQL via FastAPI's dependency injection override. This isolates tests from the production database entirely.

External services (fraud API, Redis) are mocked using `unittest.mock` — allowing tests to run without live containers while still validating integration contracts.

### Test Coverage

| Module | Tests | What Is Tested |
|--------|-------|----------------|
| `test_auth.py` | 13 | Registration, login, JWT validation, protected routes |
| `test_wallet.py` | 13 | Balance queries, deposit, withdrawal, auth enforcement |
| `test_transfer.py` | 13 | P2P transfer, balance mutations on both wallets, fraud blocking, history |
| `test_fraud.py` | 11 | API contract, fail-open on unreachable service, contract mismatch |
| `test_rate_limiting.py` | 5 | Counter logic, 429 enforcement, Redis mock |
| **Total** | **49 passed** | |

### Bugs Found by Tests

The test suite found and fixed four production bugs during development:

1. `models.wallet` → `models.Wallet` — Python is case-sensitive; wrong casing caused `AttributeError` on every transfer
2. `get_transactions()` contained transfer logic — copy-paste error put deadlock prevention code inside the history query function
3. `ValueError("Insufficient funds")` not caught by endpoint — produced 500 instead of 400
4. `/me` endpoint passing raw string to `get_current_user` — caused `AttributeError` on `.credentials`

This is the value of testing: these bugs existed in production code and were invisible until tests ran against them.

### CI/CD
Every push to `main` triggers the GitHub Actions pipeline:
- Spins up PostgreSQL and Redis service containers
- Installs all dependencies
- Runs the full test suite
- Uploads `test_results.txt` as a downloadable artifact

---

## 14. Deployment

### Local Development

```bash
git clone https://github.com/lumbol77/distributed-fintech-core
cd distributed-fintech-core
cp .env.example .env   # Configure environment variables
docker compose up --build
```

All seven services start with a single command. The wallet service auto-reloads on file changes via Uvicorn's `--reload` flag.

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing secret | Long random string |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime | `60` |
| `DATABASE_URL` | PostgreSQL connection | `postgresql://user:pass@db:5432/wallet_db` |
| `REDIS_URL` | Redis connection | `redis://redis:6379/0` |

### Service Endpoints

| Service | URL |
|---------|-----|
| API Swagger UI | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |
| Fraud API | http://localhost:8001/docs |

---

## 15. Scaling Strategy

### Current Architecture Limits

The current single-instance deployment handles moderate load. Bottlenecks at scale:

1. **PostgreSQL** — single instance, vertical scaling only
2. **wallet-service** — single Uvicorn process per container
3. **Celery** — single worker container

### Horizontal Scaling Path

**API Tier**  
Run multiple wallet-service replicas behind a load balancer (nginx or AWS ALB). Uvicorn with multiple workers: `--workers 4`. Stateless JWT auth means any replica can serve any request.

**Database Tier**  
Read replicas for transaction history queries. PgBouncer connection pooling. Partitioning the `transactions` table by `wallet_id` range for large ledger datasets.

**Celery Workers**  
Scale worker containers independently. Celery's prefork model already uses 8 processes per container. Add containers for high-notification volume.

**Redis**  
Redis Cluster for horizontal partitioning. Redis Sentinel for high-availability failover.

**Fraud Service**  
Stateless ML inference — trivially horizontally scalable. Multiple replicas behind a load balancer. Model serving could migrate to dedicated ML infrastructure (TorchServe, Triton).

---

## 16. Trade-offs & Engineering Decisions

### Why FastAPI over Django REST Framework?
FastAPI's async-first design matches the concurrency requirements of a financial API. Native OpenAPI schema generation eliminated manual documentation overhead. Pydantic validation provides runtime type safety on all request/response boundaries.

Django REST Framework was considered but rejected — its synchronous ORM and heavier framework overhead are optimized for content management, not high-throughput financial APIs.

### Why PostgreSQL over MongoDB?
Financial data is relational by nature. Wallet balances, transaction records, and user identities have strict referential integrity requirements. PostgreSQL's ACID guarantees and row-level locking primitives (`SELECT FOR UPDATE`) are purpose-built for this use case.

MongoDB's eventual consistency model is fundamentally incompatible with a ledger — you cannot have "eventually consistent" balances in a financial system.

### Why Redis over RabbitMQ?
Redis already serves the cache and rate-limiting roles. Using it as the Celery broker reduces operational complexity — one fewer infrastructure component to deploy, monitor, and maintain.

RabbitMQ would be the correct choice when message durability and dead-letter queue semantics become critical requirements. At current scale, Redis's performance characteristics exceed requirements and the operational simplicity outweighs RabbitMQ's additional guarantees.

### Why Fail-Open on Fraud Service Unavailability?
Wallet availability is more important than fraud service availability. A fraud service outage should not become a wallet outage. Every fail-open event is logged with a structured reason code, enabling:
- Alert triggering on elevated fail-open rates
- Post-incident fraud review of transactions during outage windows
- Risk team visibility without blocking user access

The alternative — fail-closed — would mean every fraud service restart, deployment, or network hiccup blocks all transfers. This is unacceptable for a financial product.

### Why Pessimistic Locking over Optimistic Locking?
Optimistic locking (check-and-retry on version conflict) generates retry storms under high concurrency. For a financial system where every conflict is a real contention event, pessimistic locking (`SELECT FOR UPDATE`) is more predictable — it queues concurrent writes rather than rejecting and retrying them.

The deterministic lock acquisition order (lower wallet ID first) eliminates deadlock risk without sacrificing the safety guarantees of pessimistic locking.

---

## 17. Future Improvements

| Priority | Improvement | Rationale |
|----------|-------------|-----------|
| High | Database migrations (Alembic) | `create_all` is not safe for production schema changes |
| High | Refresh token flow | Current JWT has no revocation mechanism |
| High | Dead letter queue for Celery | Failed notifications are currently lost |
| Medium | Redis Sentinel / Cluster | Single Redis is a single point of failure |
| Medium | Fraud model retraining pipeline | Current model is static — needs continuous learning |
| Medium | API versioning (`/v1/`) | Breaking changes require versioned endpoints |
| Medium | Async SQLAlchemy | Current sync ORM blocks the event loop on heavy queries |
| Low | WebSocket balance updates | Real-time balance push instead of polling |
| Low | Multi-currency support | Current system assumes single currency |
| Low | Spend limits and daily caps | Additional fraud prevention layer |

---

*This document reflects the system as designed and built. It is a living document — update it when architectural decisions change.*
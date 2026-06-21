# Distributed Fintech Core & Digital Wallet API

A secure, production-grade fintech backend architecture built with **FastAPI**, **PostgreSQL**, and **Redis**. This system is engineered specifically to handle high-throughput wallet allocations with strict data integrity, explicit race-condition protection, and containerized system observability.

## 🚀 Live Demo
**Interactive Documentation:** [Live Swagger UI](https://digital-wallet-api-syvf.onrender.com/docs)  
*Note: The API is hosted on Render's free tier and may take ~50 seconds to "wake up" on the first request.*

---

## 🏗️ System Architecture Design

The entire backend environment is isolated, fully containerized, and managed using a unified Docker network boundary to optimize portable infrastructure deployment.

```mermaid
graph TD
    Client[Client Browser/Postman] -->|1. Request| FastAPI
    
    subgraph Docker Container Network [Docker Compose Infrastructure Boundary]
        FastAPI[FastAPI Core Container]
        
        subgraph Data Layer
            FastAPI -->|2. Check Key| RedisCache[(Redis Idempotency Container)]
            FastAPI -->|4. Row Lock| Postgres[(PostgreSQL DB Container)]
        end
        
        subgraph Background Workers
            FastAPI -->|5. Enqueue| RedisBroker[(Redis Broker Container)]
            RedisBroker -->|6. Fetch| Celery[Celery Async Container]
        end
        
        subgraph Monitoring Stack
            Prometheus[Prometheus Container] -->|7. Scrape| FastAPI
            Grafana[Grafana Container] -->|8. Pull| Prometheus
            OTel[OpenTelemetry] -.->|Trace| FastAPI
        end
    end

    style Client fill:#f9f,stroke:#333,stroke-width:2px
    style Docker Container Network fill:#fff8e7,stroke:#f39c12,stroke-width:2px,stroke-dasharray: 5 5
    style FastAPI fill:#bbf,stroke:#333,stroke-width:2px
    style Postgres fill:#bfb,stroke:#333,stroke-width:2px
    style RedisCache fill:#ffb,stroke:#333,stroke-width:2px
    style RedisBroker fill:#ffb,stroke:#333,stroke-width:2px


Key Architectural Features
Distributed Race-Condition Prevention: Implements explicit Pessimistic Row-Level Locking (FOR UPDATE) in PostgreSQL to guarantee atomic wallet ledger entries during parallel balance modifications.

API Idempotency Middleware: Intercepts incoming transactions using a custom Redis-backed middleware layer to block duplicate network retry attempts and eliminate accidental double-deductions.

Decoupled Task Processing: Leverages a Celery Worker queue with a Redis message broker to offload secondary operations (like notifications) completely away from the primary async request-response loop.

Production-Grade Observability: Fully instrumented with OpenTelemetry for distributed transaction tracking, Prometheus for scraping time-series /metrics, and Grafana for instant dashboard monitoring visualization.

Secure Authentication Engine: Standardized JWT token-based authentication featuring securely encrypted password hashing protocols (Bcrypt).

Portable Infrastructure: Configured entirely with a 1-command Docker Compose environment, managing network isolation and environmental variable structures out of the box.

🛠️ Tech Stack Matrix
Component	Technology	Primary System Role
API Framework	FastAPI (Python)	High-performance asynchronous routing & application core
Primary Database	PostgreSQL	Relational transactional data storage & ledger tracking
Cache / Broker	Redis	Ultra-low latency idempotency mapping & Celery queue broker
Async Tasks	Celery	Distributed background worker execution loops
Metrics Collector	Prometheus	Gathering runtime execution data across container metrics
Visualization	Grafana	Production telemetry visualization interface
💻 Quickstart Local Setup
To launch this entire distributed infrastructure locally on your host environment, clone the repository and execute the single container orchestration command:

Bash
docker compose up --build

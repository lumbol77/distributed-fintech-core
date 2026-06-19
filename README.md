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

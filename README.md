# Distributed Fintech Core

## System Architecture Design

```mermaid
graph TD
    %% Define System Actors
    Client[Mobile/Postman Client] -->|1. REST Request + Idempotency-Key| FastAPI[FastAPI Core API]
    
    %% Idempotency Flow
    subgraph Data Layer
        FastAPI -->|2. Check/Lock Key| RedisCache[(Redis Idempotency Cache)]
        FastAPI -->|4. Row Lock & Execute Ledger| Postgres[(PostgreSQL Database)]
    end
    
    %% Async Job Processing
    subgraph Background Workers
        FastAPI -->|5. Enqueue Email Event| RedisBroker[(Redis Message Broker)]
        RedisBroker -->|6. Fetch Task| Celery[Celery Async Worker]
    end
    
    %% Observability Stack
    subgraph Monitoring Stack
        Prometheus[Prometheus Server] -->|7. Scrape /metrics HTTP| FastAPI
        Grafana[Grafana Dashboard] -->|8. Pull Time-Series Data| Prometheus
        OTel[OpenTelemetry Tracing] -.->|Instruments System Flow| FastAPI
    end

    %% Styling for visual appeal
    style Client fill:#f9f,stroke:#333,stroke-width:2px
    style FastAPI fill:#bbf,stroke:#333,stroke-width:2px
    style Postgres fill:#bfb,stroke:#333,stroke-width:2px
    style RedisCache fill:#ffb,stroke:#333,stroke-width:2px
    style RedisBroker fill:#ffb,stroke:#333,stroke-width:2px

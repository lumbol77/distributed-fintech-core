# Distributed Fintech Core

## System Architecture Design

```mermaid
graph TD
    Client[Client Browser/Postman] -->|1. Request| FastAPI[FastAPI Core API]
    
    subgraph Data Layer
        FastAPI -->|2. Check Key| RedisCache[(Redis Idempotency Cache)]
        FastAPI -->|4. Row Lock| Postgres[(PostgreSQL Database)]
    end
    
    subgraph Background Workers
        FastAPI -->|5. Enqueue| RedisBroker[(Redis Message Broker)]
        RedisBroker -->|6. Fetch| Celery[Celery Async Worker]
    end
    
    subgraph Monitoring Stack
        Prometheus[Prometheus Server] -->|7. Scrape| FastAPI
        Grafana[Grafana Dashboard] -->|8. Pull| Prometheus
        OTel[OpenTelemetry] -.->|Trace| FastAPI
    end

    style Client fill:#f9f,stroke:#333,stroke-width:2px
    style FastAPI fill:#bbf,stroke:#333,stroke-width:2px
    style Postgres fill:#bfb,stroke:#333,stroke-width:2px
    style RedisCache fill:#ffb,stroke:#333,stroke-width:2px
    style RedisBroker fill:#ffb,stroke:#333,stroke-width:2px

# Distributed Fintech Core

## System Architecture Design

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

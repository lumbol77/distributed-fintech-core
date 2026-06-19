# Digital Wallet API
A secure, production-ready fintech backend system built with **FastAPI** and **PostgreSQL**. This project manages user authentication, secure wallet transactions, and real-time ledger updates.

##  Live Demo
**Interactive Documentation:** [Live Swagger UI](https://digital-wallet-api-syvf.onrender.com/docs)  
*Note: The API is hosted on Render's free tier and may take ~50 seconds to "wake up" on the first request.*

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


## Key Features
* **Secure Authentication:** JWT-based login and registration with encrypted password hashing (Bcrypt).
* **Wallet Management:** Automated wallet creation upon user signup with balance tracking.
* **Transaction Engine:** Secure endpoints for deposits, withdrawals, and internal transfers.
* **Database Integrity:** Relational data modeling using SQLAlchemy with PostgreSQL.
* **Production Deployed:** Fully configured for cloud environments with environment variable management.

## 🛠 Tech Stack
* **Framework:** FastAPI (Python)
* **Database:** PostgreSQL
* **ORM:** SQLAlchemy
* **Security:** Passlib (Bcrypt), Python-Jose (JWT)
* **Deployment:** Render

##  Local Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/lumbol77/Digital-Wallet-API.git](https://github.com/lumbol77/Digital-Wallet-API.git)
   cd Digital-Wallet-API

   

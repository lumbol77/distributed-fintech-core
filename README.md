# Digital Wallet API
A secure, production-ready fintech backend system built with **FastAPI** and **PostgreSQL**. This project manages user authentication, secure wallet transactions, and real-time ledger updates.

##  Live Demo
**Interactive Documentation:** [Live Swagger UI](https://digital-wallet-api-syvf.onrender.com/docs)  
*Note: The API is hosted on Render's free tier and may take ~50 seconds to "wake up" on the first request.*

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

   

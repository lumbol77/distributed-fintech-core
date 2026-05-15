Fraud Detection ML API (Production-Ready)

A cloud-deployed Machine Learning API that detects fraudulent credit card transactions in real-time using a trained classification model.

This project demonstrates production-level ML model serving, REST API design, and cloud deployment practices used in fintech systems.

 Live API Documentation

 https://fraud-api-t9wy.onrender.com/docs

Interactive Swagger UI for testing endpoints directly from the browser.

Key Features

Real-time fraud prediction
Machine Learning model integration
RESTful API built with FastAPI
Health monitoring endpoint
Production-ready error handling
Cloud deployment on Render
Clean modular project architecture

Tech Stack

• Python
• FastAPI
• Scikit-learn
• Pandas & NumPy
• Uvicorn
• Render (Cloud Hosting)

Project Structure
fraud-detection-api/
│
├── app/
│   └── main.py              # FastAPI application & endpoints
│
├── model/
│   └── fraud_model.pkl      # Trained ML model
│
├── train.py                 # Model training pipeline
├── requirements.txt         # Project dependencies
├── README.md
└── .gitignore

API Endpoints
Health Check
GET /
Fraud Prediction
POST /predict
Example Request
{
  "features": [0.12, -1.45, ...]
}
Example Response
{
  "prediction": 1,
  "result": "fraud"
}

Model Performance
Metric	Score:
Accuracy	99.91%
Precision	92%
Recall	81%
F1 Score	86%

Local Development Setup
Clone Repository
git clone https://github.com/lumbol77/fraud-detection-api.git
cd fraud-detection-api
Create Virtual Environment
python -m venv venv
venv\Scripts\activate
Install Dependencies
pip install -r requirements.txt
Run API Server
uvicorn app.main:app --reload

Access locally at:

http://127.0.0.1:8000/docs

Future Improvements

• Docker containerization
• CI/CD pipeline enhancements
• API authentication & rate limiting
• Model performance monitoring
• AWS production deployment

 Author
Lumbol Tityem(Lawrence)

Machine Learning & Backend Engineer
📧 lumbolt@gmail.com

🔗 LinkedIn: https://www.linkedin.com/in/lumbol-tityem-zuzul-117731213

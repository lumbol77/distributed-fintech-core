import io
import httpx
from passlib.context import CryptContext
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# --- 1. PASSWORD SECURITY ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# --- 2. ML API CONNECTOR (Optimized) ---
# Make sure this matches your LIVE Fraud API URL on Render
FRAUD_API_URL = "https://fraud-api-t9wy.onrender.com/predict"

async def check_fraud_risk(amount, sender_balance, receiver_balance):
    """
    Connects the Wallet API to the Fraud Detection Microservice.
    Uses httpx for high-performance async communication.
    """
    payload = {
        "v1": float(sender_balance),
        "v2": float(receiver_balance),
        "v3": float(amount / (sender_balance + 1)), 
        "amount": float(amount)
    }

    print(f"\n [AI SECURITY] Checking transaction: ${amount}...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                FRAUD_API_URL, 
                json=payload,
                timeout=15.0  # Increased timeout for cold-starts on Render
            )

            if response.status_code == 200:
                result = response.json()
                # Use the keys your Fraud API actually sends back
                is_fraud = result.get("is_fraud", False)
                confidence = result.get("confidence", 0)
                
                print(f"[AI RESPONSE]: {'FRAUD' if is_fraud else ' SAFE'} (Confidence: {confidence})")
                return is_fraud
            
            print(f" [AI ERROR]: Server returned {response.status_code} - {response.text}")
            return False # Fail-safe: allow transaction if AI service has an issue
            
    except Exception as e:
        print(f"[CONNECTION FAILED]: {e}")
        return False # Fail-safe: allow transaction if connection fails

# --- 3. PDF GENERATOR ---
def generate_transaction_pdf(transaction, email):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, "TRANSACTION RECEIPT")
    p.setFont("Helvetica", 12)
    p.drawString(100, 720, f"User: {email}")
    
    # Safely get the amount
    amount = getattr(transaction, 'amount', 0)
    p.drawString(100, 700, f"Amount: ${amount}")
    
    # Add a timestamp if available
    timestamp = getattr(transaction, 'timestamp', 'N/A')
    p.drawString(100, 680, f"Date: {timestamp}")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
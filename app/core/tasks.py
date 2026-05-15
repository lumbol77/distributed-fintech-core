import time
from app.core.celery_app import celery_app
from app.core.logging_config import logger

@celery_app.task(name="tasks.send_transfer_notification")
def send_transfer_notification(sender_email, receiver_email, amount, tx_id):
    """
    Simulates sending an email or push notification in the background.
    """
    logger.info(f"[TASK START] Sending notification for TX: {tx_id}")
    
    # Simulate a slow network call (like an Email API)
    time.sleep(5) 
    
    logger.info(f"[TASK SUCCESS] Notification sent: {sender_email} sent ${amount} to {receiver_email}")
    return True
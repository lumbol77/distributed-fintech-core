import logging
import sys
import contextvars

# Context variable to store request_id across the execution thread
request_id_ctx = contextvars.ContextVar("request_id", default="SYSTEM")

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        # Injects the transaction ID into every log line
        record.tx_id = request_id_ctx.get()
        return super().format(record)

def setup_logging():
    logger = logging.getLogger("fintech_core")
    logger.setLevel(logging.INFO)

    logger.propagate = False  # Prevents logs from being swallowed or doubled
    if logger.hasHandlers():  # Clears old handlers during hot-reloads
        logger.handlers.clear()
    
    handler = logging.StreamHandler(sys.stdout)
    formatter = StructuredFormatter(
        '[%(tx_id)s] %(asctime)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

logger = setup_logging()


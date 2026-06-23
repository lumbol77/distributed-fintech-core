from prometheus_client import Counter, Histogram

# Track total number of processed payment transactions
TRANSACTION_COUNT = Counter(
    "wallet_transactions_total",
    "Total number of wallet transfer transactions executed.",
    labelnames=["status"]  # Labels allow you to filter by 'success' or 'failed' in Grafana
)

# Track the exact processing latency of your transaction execution blocks
TRANSACTION_LATENCY = Histogram(
    "wallet_transaction_duration_seconds",
    "Time spent executing transaction logic.",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)
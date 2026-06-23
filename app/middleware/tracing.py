from fastapi import Request
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

def setup_tracing(app):
    # 1. Initialize the global tracer provider
    provider = TracerProvider()
    trace.set_tracer_provider(provider)

    # 2. Configure the collector endpoint (pointing to our future monitoring container)
    otlp_exporter = OTLPSpanExporter(endpoint="http://tempo:4317", insecure=True)
    
    # 3. Add the processor to batch traces efficiently
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # 4. Instrument FastAPI automatically
    FastAPIInstrumentor.instrument_app(app)
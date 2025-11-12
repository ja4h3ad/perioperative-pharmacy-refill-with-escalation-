'''OpenTelemetry setup'''

from opentelemetry import trace, metrics
from prometheus_client import Counter, Histogram

# OpenTelemetry tracing for distributed flows
tracer = trace.get_tracer(__name__)

refill_latency = Histogram(
    'refill_processing_seconds',
    'Time to process refill request',
    ['intent_type', 'outcome']
)

circuit_breaker_triggers = Counter(
    'circuit_breaker_total',
    'Circuit breaker activations',
    ['trigger_type', 'agent']
)

@tracer.start_as_current_span("pharmacy_agent.safety_check")
def perform_safety_check(patient_data, medication):
    with refill_latency.labels('refill', 'safety_check').time():
        # Safety validation logic
        pass
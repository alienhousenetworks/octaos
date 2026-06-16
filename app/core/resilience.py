import logging
import pybreaker
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# Define Circuit Breakers
# Fail after 5 consecutive failures, reset check after 30 seconds
db_breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=30.0, name="db_breaker")

# Fail after 3 consecutive failures, reset check after 15 seconds
llm_breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=15.0, name="llm_breaker")

# Fail after 4 consecutive failures, reset check after 60 seconds
api_breaker = pybreaker.CircuitBreaker(fail_max=4, reset_timeout=60.0, name="api_breaker")

# Log state transition events
class LogListener(pybreaker.CircuitBreakerListener):
    def state_change(self, cb, old_state, new_state):
        logger.warning(f"Circuit Breaker '{cb.name}' state changed from {old_state.name} to {new_state.name}")

listener = LogListener()
db_breaker.add_listener(listener)
llm_breaker.add_listener(listener)
api_breaker.add_listener(listener)

# Standard Resilience Retry Policy (3 attempts, exponential backoff starting at 1s up to 10s)
standard_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
    before_sleep=lambda retry_state: logger.warning(
        f"Retrying task: attempt {retry_state.attempt_number} failed. Waiting before retry..."
    )
)

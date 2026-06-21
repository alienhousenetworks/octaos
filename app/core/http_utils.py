import logging
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

logger = logging.getLogger(__name__)

def before_retry_log(retry_state):
    if retry_state.attempt_number > 1:
        exc = retry_state.outcome.exception() if retry_state.outcome else "Unknown"
        logger.warning(
            f"Retrying {retry_state.fn.__name__} due to exception: {exc}. "
            f"Attempt {retry_state.attempt_number} of 3."
        )

# A centralized decorator for external API calls
# Waits 2 seconds, then 4, then 8. Fails after 3 attempts.
with_retry = retry(
    wait=wait_exponential(multiplier=2, min=2, max=10),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(Exception),
    before=before_retry_log,
    reraise=True
)

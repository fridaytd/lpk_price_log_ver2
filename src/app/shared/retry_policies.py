"""
Named Tenacity retry-policy decorators for all network-calling methods.

Three module-level constants are exported:

    SHEETS_READ_RETRY   — 5 attempts, exponential back-off 8–15 s  (FR21, FR22)
    SHEETS_WRITE_RETRY  — 3 attempts, exponential back-off 20–40 s (FR21, FR22)
    LAPAK_API_RETRY     — 3 attempts, fixed 0.5 s delay             (FR23)

All three:
  - Use retry_if_exception(predicate) to distinguish retriable HTTP errors
    (429, 5xx, timeouts, connect errors) from hard-fail errors (403, 404, …).
  - Set reraise=True so the original exception propagates after retries
    are exhausted (not tenacity.RetryError).
  - Log a WARNING before each sleep via before_sleep_log (FR26).

Decorator application to async def methods is handled in Story 3.2.
"""

import logging

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    wait_fixed,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Retry predicates
# ---------------------------------------------------------------------------


def _is_retryable_sheets_error(exc: BaseException) -> bool:
    """Return True for transient Sheets API errors worth retrying.

    Retried:
        - httpx.TimeoutException  (network timeout)
        - httpx.ConnectError      (connection refused / DNS failure)
        - httpx.HTTPStatusError with status 429 (rate limit) or 5xx (server error)

    NOT retried:
        - httpx.HTTPStatusError with any other 4xx (e.g. 403 Forbidden, 404 Not Found)
        - Any other exception type (programming errors, etc.)
    """
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or 500 <= code <= 599
    return False


def _is_retryable_lapak_error(exc: BaseException) -> bool:
    """Return True for transient Lapakgaming API errors worth retrying.

    Retried:
        - httpx.TimeoutException
        - httpx.ConnectError
        - httpx.HTTPStatusError with status 5xx

    NOT retried:
        - httpx.HTTPStatusError with 4xx (including 429 — not a Lapak concern)
        - Any other exception type
    """
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return 500 <= code <= 599
    return False


# ---------------------------------------------------------------------------
# Named retry-policy decorators
# ---------------------------------------------------------------------------

SHEETS_READ_RETRY = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(min=2, max=15),
    retry=retry_if_exception(_is_retryable_sheets_error),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)

SHEETS_WRITE_RETRY = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(min=2, max=40),
    retry=retry_if_exception(_is_retryable_sheets_error),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)

LAPAK_API_RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(0.5),
    retry=retry_if_exception(_is_retryable_lapak_error),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)

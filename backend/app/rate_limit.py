"""Small in-process sliding-window limiter for expensive API endpoints."""

from collections import defaultdict, deque
from dataclasses import dataclass
from hashlib import sha256
import logging
import os
from threading import Lock
import time

from fastapi import HTTPException, Request


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after: int


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
        now: float | None = None,
    ) -> RateLimitDecision:
        timestamp = time.monotonic() if now is None else now
        cutoff = timestamp - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(events[0] + window_seconds - timestamp + 0.999))
                return RateLimitDecision(False, 0, retry_after)
            events.append(timestamp)
            return RateLimitDecision(True, limit - len(events), 0)


limiter = SlidingWindowRateLimiter()


def _configured_limit(endpoint: str) -> int:
    defaults = {"recommend": 12, "chat": 60}
    default = defaults[endpoint]
    env_name = f"{endpoint.upper()}_RATE_LIMIT_PER_MINUTE"
    raw_value = os.getenv(env_name)
    if raw_value is None:
        return default
    try:
        return max(1, int(raw_value))
    except ValueError:
        logger.warning(
            "Invalid rate-limit configuration: variable=%s; using_default=%s",
            env_name,
            default,
        )
        return default


def enforce_rate_limit(request: Request, endpoint: str) -> None:
    limit = _configured_limit(endpoint)
    client_host = request.client.host if request.client else "unknown"
    decision = limiter.check(
        f"{endpoint}:{client_host}",
        limit=limit,
        window_seconds=60,
    )
    if decision.allowed:
        return

    anonymous_client = sha256(client_host.encode("utf-8")).hexdigest()[:12]
    logger.warning(
        "Rate limit exceeded: endpoint=%s client_hash=%s retry_after=%s",
        endpoint,
        anonymous_client,
        decision.retry_after,
    )
    raise HTTPException(
        status_code=429,
        detail="Too many requests. Please wait and try again.",
        headers={"Retry-After": str(decision.retry_after)},
    )

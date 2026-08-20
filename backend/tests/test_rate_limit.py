import unittest
from unittest.mock import patch

from backend.app.rate_limit import SlidingWindowRateLimiter, _configured_limit


class RateLimitTests(unittest.TestCase):
    def test_requests_within_limit_are_allowed(self) -> None:
        limiter = SlidingWindowRateLimiter()
        first = limiter.check("client", limit=2, window_seconds=60, now=10)
        second = limiter.check("client", limit=2, window_seconds=60, now=11)
        self.assertTrue(first.allowed)
        self.assertTrue(second.allowed)
        self.assertEqual(second.remaining, 0)

    def test_request_over_limit_has_retry_after(self) -> None:
        limiter = SlidingWindowRateLimiter()
        limiter.check("client", limit=1, window_seconds=60, now=10)
        blocked = limiter.check("client", limit=1, window_seconds=60, now=20)
        self.assertFalse(blocked.allowed)
        self.assertEqual(blocked.retry_after, 50)

    def test_window_expiry_allows_request_again(self) -> None:
        limiter = SlidingWindowRateLimiter()
        limiter.check("client", limit=1, window_seconds=60, now=10)
        allowed = limiter.check("client", limit=1, window_seconds=60, now=70)
        self.assertTrue(allowed.allowed)

    def test_endpoints_and_clients_have_independent_buckets(self) -> None:
        limiter = SlidingWindowRateLimiter()
        limiter.check("recommend:a", limit=1, window_seconds=60, now=10)
        self.assertTrue(limiter.check("chat:a", limit=1, window_seconds=60, now=11).allowed)
        self.assertTrue(limiter.check("recommend:b", limit=1, window_seconds=60, now=11).allowed)

    def test_invalid_configuration_uses_safe_default(self) -> None:
        with patch.dict(
            "os.environ",
            {"RECOMMEND_RATE_LIMIT_PER_MINUTE": "not-a-number"},
        ):
            self.assertEqual(_configured_limit("recommend"), 12)


if __name__ == "__main__":
    unittest.main()

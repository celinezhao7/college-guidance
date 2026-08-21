import unittest

from backend.app.streaming import resilient_stream, stream_error_message


class ResilientStreamTests(unittest.TestCase):
    def test_retries_once_when_failure_happens_before_output(self) -> None:
        attempts = 0

        def factory():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise ConnectionError("temporary")
            return iter(["Second choice: PIQ #3"])

        self.assertEqual(
            "".join(resilient_stream(factory, language="en")),
            "Second choice: PIQ #3",
        )
        self.assertEqual(attempts, 2)

    def test_does_not_restart_after_partial_output(self) -> None:
        attempts = 0

        def factory():
            nonlocal attempts
            attempts += 1

            def chunks():
                yield "Partial answer"
                raise ConnectionError("interrupted")

            return chunks()

        result = "".join(resilient_stream(factory, language="en"))
        self.assertEqual(attempts, 1)
        self.assertIn("Partial answer", result)
        self.assertIn("connection was interrupted", result)

    def test_missing_scorecard_key_is_actionable_and_not_retried(self) -> None:
        attempts = 0

        def factory():
            nonlocal attempts
            attempts += 1
            raise RuntimeError("COLLEGE_SCORECARD_API_KEY is missing from .env")

        result = "".join(resilient_stream(factory, language="en"))
        self.assertEqual(1, attempts)
        self.assertIn("not configured", result)
        self.assertNotIn(".env", result)

    def test_scorecard_rate_limit_and_outage_are_distinguished(self) -> None:
        self.assertIn(
            "rate-limiting",
            stream_error_message(RuntimeError("College Scorecard returned HTTP 429"), "en"),
        )
        self.assertIn(
            "无法连接 College Scorecard",
            stream_error_message(RuntimeError("Could not reach College Scorecard: timeout"), "zh"),
        )


if __name__ == "__main__":
    unittest.main()

import unittest

from backend.app.streaming import resilient_stream


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


if __name__ == "__main__":
    unittest.main()

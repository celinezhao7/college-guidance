"""Resilience helpers for user-visible streaming responses."""

from collections.abc import Callable, Iterable, Iterator
import logging


logger = logging.getLogger(__name__)


def resilient_stream(
    factory: Callable[[], Iterable[str]],
    *,
    language: str,
) -> Iterator[str]:
    """Retry a transport failure before first output and keep streaming errors user-visible."""
    emitted = False
    for attempt in range(2):
        try:
            for chunk in factory():
                if chunk:
                    emitted = True
                    yield chunk
            return
        except Exception as exc:
            logger.warning(
                "Recommendation stream failed: attempt=%s emitted=%s error_type=%s",
                attempt + 1,
                emitted,
                type(exc).__name__,
            )
            if emitted or attempt == 1:
                yield (
                    "\n\n生成过程中连接中断，请重试刚才的问题。"
                    if language == "zh"
                    else "\n\nThe generation connection was interrupted. Please retry your last question."
                )
                return

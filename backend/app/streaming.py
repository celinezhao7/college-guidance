"""Resilience helpers for user-visible streaming responses."""

from collections.abc import Callable, Iterable, Iterator
import logging


logger = logging.getLogger(__name__)


def stream_error_message(exc: Exception, language: str) -> str:
    """Return a safe, actionable message without exposing credentials or internals."""
    detail = str(exc).lower()
    if "college_scorecard_api_key" in detail:
        return (
            "大学数据服务尚未配置。请联系管理员添加 College Scorecard API key。"
            if language == "zh"
            else "The college-data service is not configured. Ask an administrator to add the College Scorecard API key."
        )
    if "college scorecard" in detail and "http 429" in detail:
        return (
            "College Scorecard 当前请求过多，请稍后重试；你的筛选条件不会丢失。"
            if language == "zh"
            else "College Scorecard is rate-limiting requests. Please retry shortly; your filters are preserved."
        )
    if "college scorecard" in detail and any(token in detail for token in ("could not", "timeout", "timed out", "unreachable")):
        return (
            "暂时无法连接 College Scorecard。请稍后使用相同筛选条件重试。"
            if language == "zh"
            else "College Scorecard could not be reached. Please retry shortly with the same filters."
        )
    return (
        "生成过程中连接中断，请重试刚才的问题。"
        if language == "zh"
        else "The generation connection was interrupted. Please retry your last question."
    )


def is_non_retryable(exc: Exception) -> bool:
    return "college_scorecard_api_key" in str(exc).lower()


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
            if emitted or attempt == 1 or is_non_retryable(exc):
                yield f"\n\n{stream_error_message(exc, language)}"
                return

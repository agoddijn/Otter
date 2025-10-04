from __future__ import annotations

from functools import wraps
from typing import Any, Awaitable, Callable, Dict, Tuple, TypeVar

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


class ResponseCache:
    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}

    def _generate_key(
        self, func_name: str, args: Tuple[Any, ...], kwargs: Dict[str, Any]
    ) -> str:
        return f"{func_name}:{args}:{sorted(kwargs.items())}"


cache = ResponseCache()


def cache_result(ttl: int = 300) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            _ = ttl  # placeholder usage
            key = cache._generate_key(func.__name__, args, kwargs)
            return cache._cache.get(key)  # naive stub

        return wrapper  # type: ignore[return-value]

    return decorator

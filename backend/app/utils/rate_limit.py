from collections import defaultdict, deque
from threading import Lock
from time import time

from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    def __init__(self):
        self._requests = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, max_requests: int, window_seconds: int) -> None:
        now = time()

        with self._lock:
            recent_requests = self._requests[key]

            while recent_requests and recent_requests[0] <= now - window_seconds:
                recent_requests.popleft()

            if len(recent_requests) >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Too many AI requests. Try again in about {window_seconds} seconds."
                    ),
                )

            recent_requests.append(now)


rate_limiter = InMemoryRateLimiter()


def get_client_rate_limit_key(request: Request, scope: str) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else ""

    if not client_ip and request.client:
        client_ip = request.client.host

    if not client_ip:
        client_ip = "unknown"

    return f"{scope}:{client_ip}"

from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class InMemorySlidingWindowLimiter:
    def __init__(self) -> None:
        self._values: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, *, limit: int, window_seconds: int, now: float | None = None) -> tuple[bool, int]:
        now = time.time() if now is None else now
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._values[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry = max(1, int(window_seconds - (now - bucket[0])))
                return False, retry
            bucket.append(now)
            return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-principal/path abuse limiter. Redis-backed deployments can replace the limiter via app.state."""
    def __init__(self, app, *, requests_per_minute: int = 120, mutation_requests_per_minute: int = 40) -> None:
        super().__init__(app)
        self.read_limit = requests_per_minute
        self.write_limit = mutation_requests_per_minute
        self.fallback = InMemorySlidingWindowLimiter()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method == "OPTIONS" or request.url.path.endswith("/health"):
            return await call_next(request)
        identity = getattr(request.state, "identity", None)
        principal = getattr(identity, "principal", None)
        if principal is not None:
            actor_material = str(getattr(principal, "user_id", "authenticated"))
        else:
            bearer = request.headers.get("Authorization", "")
            actor_material = bearer if bearer.startswith("Bearer ") else (request.client.host if request.client else "anonymous")
        tenant = getattr(principal, "tenant_id", None) or request.headers.get("X-Tenant-Id", "unknown")
        actor_hash = hashlib.sha256(actor_material.encode()).hexdigest()[:24]
        route_group = request.url.path.rsplit("/", 1)[0][:160]
        limit = self.read_limit if request.method in {"GET", "HEAD"} else self.write_limit
        limiter = getattr(request.app.state, "rate_limiter", self.fallback)
        allowed, retry_after = limiter.allow(f"{tenant}:{actor_hash}:{request.method}:{route_group}", limit=limit, window_seconds=60)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "rate_limited", "message": "Request rate limit exceeded"}},
                headers={"Retry-After": str(retry_after), "Cache-Control": "no-store"},
            )
        response = await call_next(request)
        response.headers.setdefault("X-RateLimit-Limit", str(limit))
        return response


class RedisSlidingWindowLimiter:
    """Atomic Redis sliding-window limiter for horizontally scaled API replicas."""
    _SCRIPT = """
local key=KEYS[1]
local now=tonumber(ARGV[1])
local window=tonumber(ARGV[2])
local limit=tonumber(ARGV[3])
local member=ARGV[4]
redis.call('ZREMRANGEBYSCORE',key,0,now-window)
local count=redis.call('ZCARD',key)
if count >= limit then
  local oldest=redis.call('ZRANGE',key,0,0,'WITHSCORES')
  local retry=1
  if oldest[2] then retry=math.max(1,math.ceil(window-(now-tonumber(oldest[2])))) end
  return {0,retry}
end
redis.call('ZADD',key,now,member)
redis.call('EXPIRE',key,math.ceil(window)+1)
return {1,0}
"""
    def __init__(self, redis_url: str) -> None:
        import redis
        self.client=redis.Redis.from_url(redis_url,decode_responses=True)
        self.script=self.client.register_script(self._SCRIPT)
    def allow(self,key:str,*,limit:int,window_seconds:int,now:float|None=None):
        import uuid
        now=time.time() if now is None else now
        result=self.script(keys=[f"medclaimiq:ratelimit:{key}"],args=[now,window_seconds,limit,f"{now}:{uuid.uuid4().hex}"]); return bool(int(result[0])),int(result[1])

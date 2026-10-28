"""Tiny in-memory rate limiter (per IP + endpoint). Good enough for a single-process demo.
For multiple workers/servers use Flask-Limiter with Redis instead."""
import time
from collections import defaultdict, deque
from functools import wraps
from flask import request, current_app, abort

_hits = defaultdict(deque)


def rate_limit(max_calls, per_seconds):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if current_app.config.get("RATELIMIT_ENABLED") and request.method == "POST":
                key = (request.remote_addr, request.endpoint)
                now = time.time()
                q = _hits[key]
                while q and now - q[0] > per_seconds:
                    q.popleft()
                if len(q) >= max_calls:
                    abort(429)
                q.append(now)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def reset():
    _hits.clear()

import time
from fastapi import Request
from fastapi.responses import JSONResponse

# In-memory store (fine for this project)
request_store = {}

AUTH_LIMIT = 10
DEFAULT_LIMIT = 60
WINDOW = 60  # seconds


def get_client_key(request: Request):
    """
    Identify the user:
    - Auth routes → use IP
    - Other routes → use user ID (if authenticated)
    """
    if request.url.path.startswith("/auth"):
        return request.client.host

    user = getattr(request.state, "user", None)
    if user:
        return str(user.id)

    return request.client.host


async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path

    if path.startswith("/auth"):
        limit = AUTH_LIMIT
    else:
        limit = DEFAULT_LIMIT

    key = get_client_key(request)
    now = time.time()

    if key not in request_store:
        request_store[key] = []

    # Remove expired timestamps
    request_store[key] = [
        t for t in request_store[key] if now - t < WINDOW
    ]

    if len(request_store[key]) >= limit:
        return JSONResponse(
            status_code=429,
            content={
                "status": "error",
                "message": "Too many requests"
            }
        )

    request_store[key].append(now)

    response = await call_next(request)

    # Optional (nice bonus)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(limit - len(request_store[key]))

    return response
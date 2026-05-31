"""Auth middleware for Play — protects all routes except /login, /api/session, and /health."""

import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse


PROTECTED_PATHS = re.compile(r"^(?!/login|/api/session|/health|/ready|/static)(/.*)?$")
COOKIE_NAME = "play_session"


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path

        if not PROTECTED_PATHS.match(path):
            return await call_next(request)

        player = request.cookies.get(COOKIE_NAME)
        if not player:
            return RedirectResponse(url="/login", status_code=303)

        request.state.current_player = player
        return await call_next(request)

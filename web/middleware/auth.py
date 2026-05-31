"""Auth middleware for Play — protects all routes except /login, /api/session, and /health."""

import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

from core.db import Session, async_session
from sqlalchemy import select


PROTECTED_PATHS = re.compile(r"^(?!/login|/api/session|/health|/ready|/static)(/.*)?$")
COOKIE_NAME = "play_session"


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path

        if not PROTECTED_PATHS.match(path):
            return await call_next(request)

        token = request.cookies.get(COOKIE_NAME)
        if not token:
            return RedirectResponse(url="/login", status_code=303)

        async with async_session() as session:
            result = await session.execute(select(Session).where(Session.token == token))
            sess = result.scalars().one_or_none()

        if not sess:
            return RedirectResponse(url="/login", status_code=303)

        request.state.current_player = sess.player_name
        return await call_next(request)

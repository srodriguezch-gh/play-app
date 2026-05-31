"""Authentication routes for Play."""

import logging
from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from core.auth import authenticate_player, generate_session_token, validate_pin
from core.db import Player, Session, async_session
from sqlalchemy import select, delete

logger = logging.getLogger(__name__)
router = APIRouter()

PLAYER_COOKIE = "play_session"
VALID_PLAYERS = {"Emma", "Mateo", "Dad"}
SESSION_TTL = 60 * 60 * 24 * 30  # 30 days


def _build_redirect(url: str, error: str = None) -> RedirectResponse:
    if error:
        import urllib.parse
        return RedirectResponse(url=f"{url}?error={urllib.parse.quote(error)}", status_code=303)
    return RedirectResponse(url=url, status_code=303)


def _get_player_from_token(token: str) -> str | None:
    """Look up player name by session token. Returns None if token invalid."""
    # Note: called from sync context (middleware, socket environ parsing)
    # so we run in a blocking sync pool
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(_get_player_from_token_sync, token)
            return future.result(timeout=5)
    return asyncio.run(_get_player_from_token_async(token))


def _get_player_from_token_async(token: str) -> str | None:
    async def _lookup():
        async with async_session() as session:
            result = await session.execute(select(Session).where(Session.token == token))
            sess = result.scalars().one_or_none()
            return sess.player_name if sess else None
    try:
        return asyncio.run(_lookup())
    except Exception:
        return None


def _get_player_from_token_sync(token: str) -> str | None:
    """Sync wrapper for use in sync contexts."""
    return _get_player_from_token_async(token)


async def _create_session(player_name: str) -> str:
    """Create a new session token for the player. Returns the token."""
    token = generate_session_token()
    async with async_session() as session:
        session.add(Session(token=token, player_name=player_name))
        await session.commit()
    return token


async def _delete_session(token: str) -> None:
    async with async_session() as session:
        await session.execute(delete(Session).where(Session.token == token))
        await session.commit()


@router.get("/login")
async def login_page(request: Request):
    if request.cookies.get(PLAYER_COOKIE):
        return RedirectResponse(url="/", status_code=303)
    templates = Jinja2Templates(directory="web/templates")
    error = request.query_params.get("error", "")
    return templates.TemplateResponse("login.html", {"request": request, "error": error, "current_player": None})


@router.post("/login")
async def login(request: Request, response: Response, name: str = Form(...), pin: str = Form(...)):
    client_ip = request.client.host if request.client else "unknown"

    if name not in VALID_PLAYERS:
        logger.warning(f"Login attempt with invalid player: {name} from {client_ip}")
        return _build_redirect("/login", "Invalid player")

    valid, msg = validate_pin(pin)
    if not valid:
        return _build_redirect("/login", msg)

    success, auth_msg = await authenticate_player(name, pin, client_ip)
    if not success:
        logger.warning(f"Failed login for {name} from {client_ip}: {auth_msg}")
        return _build_redirect("/login", auth_msg)

    token = await _create_session(name)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=PLAYER_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_TTL,
        secure=request.url.scheme == "https",
    )
    logger.info(f"Successful login for {name} from {client_ip}")
    return response


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(PLAYER_COOKIE)
    if token:
        await _delete_session(token)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(PLAYER_COOKIE)
    logger.info(f"Logout for token={token[:8]}...")
    return response


@router.get("/api/session")
async def get_session(request: Request):
    token = request.cookies.get(PLAYER_COOKIE)
    if not token:
        return {"player": None}
    player_name = await _get_player_from_token_async(token)
    return {"player": player_name}

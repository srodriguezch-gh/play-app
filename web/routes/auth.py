"""Authentication routes for Play."""

import logging
from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from core.auth import authenticate_player, generate_session_token, validate_pin
from core.db import Player, async_session
from sqlalchemy import select

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


@router.get("/login")
async def login_page(request: Request):
    if request.cookies.get(PLAYER_COOKIE):
        return RedirectResponse(url="/", status_code=303)
    templates = Jinja2Templates(directory="web/templates")
    error = request.query_params.get("error", "")
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


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

    async with async_session() as session:
        result = await session.execute(select(Player).where(Player.name == name))
        player = result.scalars().one_or_none()
        if not player:
            return _build_redirect("/login", "Player not found")

    token = generate_session_token()
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=PLAYER_COOKIE,
        value=name,
        httponly=True,
        samesite="lax",
        max_age=SESSION_TTL,
        secure=request.url.scheme == "https",
    )
    logger.info(f"Successful login for {name} from {client_ip}")
    return response


@router.post("/logout")
async def logout(request: Request, response: Response):
    player = request.cookies.get(PLAYER_COOKIE, "unknown")
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(PLAYER_COOKIE)
    logger.info(f"Logout for {player}")
    return response


@router.get("/api/session")
async def get_session(request: Request):
    player = request.cookies.get(PLAYER_COOKIE)
    if not player:
        return {"player": None}
    return {"player": player}

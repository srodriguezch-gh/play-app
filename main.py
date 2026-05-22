"""Game Hub — FastAPI + Socket.io server."""

import logging
import os
from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

from core.config import get_settings
from core.logging_config import setup_logging
from web.routes import players, tasks
from core.game_manager import game_manager
from web import socket_events

settings = get_settings()
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} {settings.APP_VERSION}")
    game_manager.cleanup()
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

templates = Jinja2Templates(directory="web/templates")

# Routes
app.include_router(players.router)
app.include_router(tasks.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    return {"status": "ready"}


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/leaderboard")
async def leaderboard(request: Request):
    return templates.TemplateResponse("leaderboard.html", {"request": request})


@app.get("/tasks")
async def tasks_page(request: Request):
    return templates.TemplateResponse("task_hub.html", {"request": request})


@app.get("/games/chess")
async def chess_page(request: Request):
    return templates.TemplateResponse("game/chess.html", {"request": request})


@app.get("/games/tictactoe")
async def tictactoe_page(request: Request):
    return templates.TemplateResponse("game/tictactoe.html", {"request": request})


@app.get("/games/{game}")
async def game_page(request: Request, game: str):
    template_path = f"game/{game}.html"
    template_dir = os.path.join(os.path.dirname(__file__), "web/templates/game")
    if not os.path.exists(os.path.join(os.path.dirname(__file__), "web/templates", template_path)):
        return templates.TemplateResponse("errors/404.html", {"request": request}, status_code=404)
    return templates.TemplateResponse(template_path, {"request": request})


# Error handlers
@app.exception_handler(404)
async def not_found(request: Request, exc):
    return templates.TemplateResponse("errors/404.html", {"request": request}, status_code=404)


@app.exception_handler(500)
async def server_error(request: Request, exc):
    logger.error(f"500 error: {exc}")
    return templates.TemplateResponse("errors/500.html", {"request": request}, status_code=500)


# Static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Mount silrod-ui shared CSS
try:
    from silrod_ui import get_static_dir
    silrod_static = get_static_dir()
    if os.path.exists(silrod_static):
        app.mount("/static/silrod", StaticFiles(directory=silrod_static), name="silrod-static")
except ImportError:
    pass

# Socket.io server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.cors_origins_list,
)

socket_events.init_socket(sio)
socket_events.register_events(sio)
socket_app = socketio.ASGIApp(sio, app)
# Play — Implementation Plan

> **Status:** ✅ IMPLEMENTED — running on NUC at `http://192.168.5.99:3001`

## What's Built

- PIN authentication (first login sets PIN, subsequent logins verify)
- bcrypt hashing, rate limiting (5 attempts/5min lockout)
- Session cookie: HttpOnly, SameSite=lax, 30-day TTL
- AuthMiddleware protecting all routes except `/login`, `/health`, `/static`
- Dashboard: player greeting, wallet balance, stats, game grid
- Leaderboard: sorted by wins, highlights current player
- Task hub: per-child tasks, PIN-protected approval → wallet credit
- 9 games: chess, tictactoe, connectfour, rps, snake, hangman, checkers, simonsays, wordsearch
- Socket.IO for real-time game events and challenge system
- Leaderboard updates via socket on game end

## Tech Stack
- FastAPI + Uvicorn + Python 3.12
- python-socketio for real-time game communication
- Jinja2 + HTMX for dashboard/pages
- PostgreSQL via SQLAlchemy async
- silrod-ui for shared shell/CSS/JS
- python-chess for server-side chess validation

## Routes
- `GET /login`, `POST /login`, `POST /logout` — auth
- `GET /` — dashboard
- `GET /leaderboard` — rankings
- `GET /tasks` — task hub
- `GET /games/{game}` — individual game pages
- `POST /api/tasks/{id}/approve` — PIN-verified approval → wallet credit

## Key Decisions
- silrod_core mount at `/app/silrod_core:ro` with PYTHONPATH override
- Game transactions recorded, not deleted on payout
- Server-side move validation for chess, tictactoe, connectfour
- `gameEnd` socket event credits wallet (+10) and updates stats
- `loser` key fix (was `losers`) so stats persist correctly
- Local `web/templates/macros/_shell.html` overrides container's stale silrod-ui

## Naming History
- Originally: `game-hub-python` repo + `bosgame-play-app:latest` image
- Renamed 2026-05-31: `play-app` repo + `play-app:latest` image
- App name: `Play` (was `Game Hub`)
- DB: `gamehub` (unchanged)
- In-memory game state for active matches, persisted to DB on game end
- Python-chess for chess logic, chess engine subprocess for AI moves
- silrod-core for config, logging, base templates, and shared CSS

**Tech Stack:** Python 3.12, FastAPI, python-socketio, SQLAlchemy, python-chess, pydantic, jinja2, HTMX, uvicorn

---

## Phase 1: Project Scaffold

### Task 1: Create project structure and pyproject.toml

**Files:**
- Create: `/home/silvio/projects/game-hub-python/pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[project]
name = "game-hub"
version = "0.1.0"
description = "Family game hub — chess, tic-tac-toe, and more"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "python-socketio>=5.11.0",
    "python-chess>=1.9.0",
    "sqlalchemy>=2.0",
    "asyncpg>=0.30",
    "psycopg2-binary>=2.9",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "passlib[bcrypt]>=1.7",
    "jinja2>=3.1",
    "python-multipart>=0.0.22",
]

[project.optional-dependencies]
dev = ["pytest>=9.0", "pytest-asyncio>=0.23", "ruff>=0.9"]
```

**Step 1:** Create the file with content above.

**Step 2:** Run `cd /home/silvio/projects/game-hub-python && python3 -c "import tomllib; tomllib.loads(open('pyproject.toml').read())"` to validate TOML syntax.

---

### Task 2: Create config.py using silrod-core settings pattern

**Files:**
- Create: `/home/silvio/projects/game-hub-python/core/config.py`

```python
"""Configuration for game-hub using pydantic-settings + silrod-core pattern."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GAMEHUB_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )

    APP_NAME: str = "game-hub"
    APP_VERSION: str = "0.1.0"
    PORT: int = 3001

    DB_USER: str = "gamehub"
    DB_HOST: str = "postgres"
    DB_NAME: str = "gamehub"
    DB_PASSWORD: str = ""
    DB_PORT: int = 5432

    DATABASE_URL: str = ""  # Built from components if empty

    NTFY_TOPIC: str = "9935-srodriguezch-alerts"

    CORS_ORIGINS: str = "https://play.silrod.org,http://localhost:3001"

    RATE_LIMIT_WINDOW_MS: int = 60000
    RATE_LIMIT_MAX_REQUESTS: int = 100

    def build_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

**Step 1:** Create the file.

**Step 2:** Run `cd /home/silvio/projects/game-hub-python && python3 -c "from core.config import get_settings; s = get_settings(); print(s.APP_NAME)"` — expected: `game-hub`

---

### Task 3: Create logging_config.py with JSON formatter

**Files:**
- Create: `/home/silvio/projects/game-hub-python/core/logging_config.py`

```python
"""JSON logging configuration for game-hub."""

import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            payload["exception"] = self.formatException(record.exc_info)
        return f"{json.dumps(payload)}\n"


import json  # noqa: E402


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    for h in root.handlers[:]:
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JSONFormatter())
    root.addHandler(handler)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("socketio").setLevel(logging.WARNING)
```

---

### Task 4: Create main.py FastAPI app skeleton with Socket.io

**Files:**
- Create: `/home/silvio/projects/game-hub-python/main.py`

```python
"""Game Hub — FastAPI + Socket.io server."""

import logging
from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.config import get_settings
from core.logging_config import setup_logging

settings = get_settings()
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} {settings.APP_VERSION}")
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

# Socket.io server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.cors_origins_list,
)

# Mount Socket.io ASGI app
socket_app = socketio.ASGIApp(sio, app)

# Templates & Static
templates = Jinja2Templates(directory="web/templates")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    return {"status": "ready"}
```

**Step 1:** Create the file.

**Step 2:** Run `cd /home/silvio/projects/game-hub-python && python3 -c "from main import app; print('FastAPI app loads OK')"` — expected: output with no errors.

---

### Task 5: Create Dockerfile

**Files:**
- Create: `/home/silvio/projects/game-hub-python/Dockerfile`

```dockerfile
# Build stage
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r pyproject.toml

# Runtime stage
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=America/New_York

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3001/health || exit 1

CMD ["uvicorn", "main:socket_app", "--host", "0.0.0.0", "--port", "3001", "--factory"]
```

---

## Phase 2: Database Models

### Task 6: Create SQLAlchemy models

**Files:**
- Create: `/home/silvio/projects/game-hub-python/core/db.py`

```python
"""SQLAlchemy models for game-hub."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    JSON,
    Index,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.build_database_url(), echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    pin_hash = Column(Text, nullable=True)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    game_wins = Column(JSON, default=dict)  # {"chess": 5, "tictactoe": 3}
    selfie = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    child_name = Column(String(100), nullable=False)
    task_description = Column(Text, nullable=False)
    points = Column(Integer, default=1)
    is_completed = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)
    is_paid = Column(Boolean, default=False)
    is_recurring = Column(Boolean, default=False)
    series_total = Column(Integer, default=1)
    series_count = Column(Integer, default=0)
    last_increment_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    child_name = Column(String(100), nullable=False)
    amount = Column(Numeric, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PlayerCollection(Base):
    __tablename__ = "player_collections"

    id = Column(Integer, primary_key=True)
    player_name = Column(String(100), nullable=False)
    game_id = Column(String(100), nullable=False)
    collection_data = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_player_game", "player_name", "game_id", unique=True),
    )


async def init_db():
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
```

**Step 1:** Create the file.

**Step 2:** Verify syntax: `cd /home/silvio/projects/game-hub-python && python3 -c "from core.db import Player, Task, Transaction; print('Models OK')"`

---

### Task 7: Create DB init script with default players

**Files:**
- Create: `/home/silvio/projects/game-hub-python/core/db_init.py`

```python
"""Initialize game-hub database with schema and default players."""

import asyncio
import logging

from sqlalchemy import text

from core.config import get_settings
from core.db import Base, engine, get_session, Player

logger = logging.getLogger(__name__)

DEFAULT_PLAYERS = ["Dad", "Emma", "Mateo", "Calypso"]


async def init_schema():
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema created")


async def init_players():
    """Ensure default players exist."""
    async for session in get_session():
        for name in DEFAULT_PLAYERS:
            result = await session.execute(
                text("SELECT 1 FROM players WHERE name = :name"),
                {"name": name}
            )
            if not result.fetchone():
                session.add(Player(name=name, game_wins={}))
                logger.info(f"Created player: {name}")
        await session.commit()


async def init_tasks_schema():
    """Ensure tasks table has all required columns."""
    async for session in get_session():
        columns_to_add = [
            ("is_approved", "BOOLEAN DEFAULT FALSE"),
            ("is_paid", "BOOLEAN DEFAULT FALSE"),
            ("is_recurring", "BOOLEAN DEFAULT FALSE"),
            ("series_total", "INTEGER DEFAULT 1"),
            ("series_count", "INTEGER DEFAULT 0"),
            ("last_increment_at", "TIMESTAMP"),
        ]
        for col_name, col_def in columns_to_add:
            try:
                await session.execute(
                    text(f"ALTER TABLE tasks ADD COLUMN IF NOT EXISTS {col_name} {col_def}")
                )
            except Exception:
                pass
        await session.commit()


async def main():
    settings = get_settings()
    logger.info(f"Initializing game-hub database at {settings.DB_HOST}")
    await init_schema()
    await init_players()
    await init_tasks_schema()
    logger.info("Database initialization complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
```

---

## Phase 3: Auth (PIN-based)

### Task 8: Create auth.py with PIN hash verification

**Files:**
- Create: `/home/silvio/projects/game-hub-python/core/auth.py`

```python
"""PIN-based authentication for game-hub players."""

import re
from typing import Optional

from passlib.context import CryptContext

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import Player

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_pin(pin: str) -> str:
    """Hash a 4-digit PIN."""
    return pwd_context.hash(pin)


def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """Verify a plain PIN against its hash."""
    return pwd_context.verify(plain_pin, hashed_pin)


def validate_pin(pin: str) -> tuple[bool, str]:
    """Validate PIN format (must be exactly 4 digits)."""
    if not pin or not isinstance(pin, str):
        return False, "PIN is required"
    if len(pin) != 4 or not re.match(r"^\d{4}$", pin):
        return False, "PIN must be exactly 4 digits"
    return True, ""


async def get_player(session: AsyncSession, name: str) -> Optional[Player]:
    """Fetch a player by name."""
    result = await session.execute(select(Player).where(Player.name == name))
    return result.scalar_one_or_none()


async def login_player(session: AsyncSession, name: str, pin: str) -> tuple[bool, str]:
    """Attempt player login. Returns (success, message)."""
    valid, msg = validate_pin(pin)
    if not valid:
        return False, msg

    player = await get_player(session, name)
    if not player:
        return False, "Player not found"

    if not player.pin_hash:
        # First time login — set PIN
        player.pin_hash = hash_pin(pin)
        await session.commit()
        return True, "PIN set successfully"

    if verify_pin(pin, player.pin_hash):
        return True, "Logged in"

    return False, "Incorrect PIN"
```

**Step 1:** Create the file.

**Step 2:** Run `cd /home/silvio/projects/game-hub-python && python3 -c "from core.auth import hash_pin, verify_pin; h = hash_pin('1234'); print(verify_pin('1234', h)); print(verify_pin('0000', h))"` — expected: `True`, `False`

---

## Phase 4: Game State Manager

### Task 9: Create game_manager.py for in-memory game state

**Files:**
- Create: `/home/silvio/projects/game-hub-python/core/game_manager.py`

```python
"""In-memory game state manager for active game sessions."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GameInstance:
    """Base class for a game in memory."""
    room_id: str
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    last_updated: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


@dataclass
class ChessGameInstance(GameInstance):
    """Chess game with FEN state."""
    fen: str = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


class GameManager:
    """Manages in-memory game state and online users."""

    def __init__(self):
        self.games: dict[str, GameInstance] = {}
        self.online_users: dict[str, str] = {}  # {socket_id: player_name}
        self.rate_limit_store: dict[str, dict] = {}
        self._cleanup_interval = 3600  # Cleanup every hour
        self._start_cleanup_task()

    def _start_cleanup_task(self):
        asyncio.create_task(self._cleanup_loop())

    async def _cleanup_loop(self):
        while True:
            await asyncio.sleep(self._cleanup_interval)
            await self._cleanup_stale_games()

    async def _cleanup_stale_games(self):
        now = datetime.now(timezone.utc).timestamp()
        expiry = 24 * 3600  # 24 hours
        cleaned = 0
        for room_id in list(self.games.keys()):
            if now - self.games[room_id].last_updated > expiry:
                del self.games[room_id]
                cleaned += 1
        if cleaned:
            logger.info(f"Cleaned up {cleaned} stale game(s)")

    def set_online(self, socket_id: str, player_name: str):
        self.online_users[socket_id] = player_name

    def remove_online(self, socket_id: str) -> str | None:
        return self.online_users.pop(socket_id, None)

    def get_online_users(self) -> list[str]:
        return list(self.online_users.values())

    def get_online_count(self) -> int:
        return len(self.online_users)

    def get_online_status(self) -> list[str]:
        return list(self.online_users.values())

    # Rate limiting
    def check_rate_limit(self, ip: str, window_ms: int = 60000, max_requests: int = 100) -> bool:
        now = datetime.now(timezone.utc).timestamp() * 1000
        record = self.rate_limit_store.get(ip)
        if not record or now - record["window_start"] > window_ms:
            self.rate_limit_store[ip] = {"count": 1, "window_start": now}
            return True
        if record["count"] >= max_requests:
            return False
        record["count"] += 1
        return True

    # Chess
    def get_or_create_chess(self, room_id: str) -> ChessGameInstance:
        if room_id not in self.games:
            self.games[room_id] = ChessGameInstance(room_id=room_id)
        elif not isinstance(self.games[room_id], ChessGameInstance):
            self.games[room_id] = ChessGameInstance(room_id=room_id)
        game = self.games[room_id]
        game.last_updated = datetime.now(timezone.utc).timestamp()
        return game

    def update_chess_fen(self, room_id: str, fen: str):
        game = self.get_or_create_chess(room_id)
        game.fen = fen

    def reset_chess(self, room_id: str):
        if room_id in self.games:
            self.games[room_id].last_updated = datetime.now(timezone.utc).timestamp()

    def get_game(self, room_id: str) -> GameInstance | None:
        return self.games.get(room_id)

    def delete_game(self, room_id: str):
        if room_id in self.games:
            del self.games[room_id]


# Global game manager instance
game_manager = GameManager()
```

---

## Phase 5: Chess AI

### Task 10: Create chess_ai.py with minimax engine

**Files:**
- Create: `/home/silvio/projects/game-hub-python/core/chess_ai.py`

```python
"""Chess AI using minimax search with alpha-beta pruning."""

import chess
import random
import logging

logger = logging.getLogger(__name__)

# Piece values for evaluation
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}

# Square tables for positional evaluation
PAWN_TABLE = [
    0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
    5,  5, 10, 25, 25, 5,  5,  5,
    0,  0,  0, 20, 20,  0,  0,  0,
    5, -5,-10,  0,  0,-10, -5,  5,
    5, 10, 10,-20,-20, 10, 10,  5,
    0,  0,  0,  0,  0,  0,  0,  0,
]

KNIGHT_TABLE = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50,
]

def evaluate_board(board: chess.Board) -> float:
    """Simple evaluation: material + position."""
    if board.is_checkmate():
        return -99999 if board.turn else 99999
    if board.is_stalemate() or board.is_draw():
        return 0

    score = 0
    for piece_type in chess.PIECE_TYPES:
        for piece in board.piece_map().values():
            if piece.piece_type == piece_type:
                value = PIECE_VALUES[piece_type]
                square = piece.square
                if piece.color == chess.WHITE:
                    score += value
                    if piece_type == chess.PAWN:
                        score += PAWN_TABLE[chess.square_file(square) + 8 * (7 - chess.square_rank(square))]
                    elif piece_type == chess.KNIGHT:
                        score += KNIGHT_TABLE[square]
                else:
                    score -= value
                    if piece_type == chess.PAWN:
                        score -= PAWN_TABLE[chess.square_file(square) + 8 * chess.square_rank(square)]
                    elif piece_type == chess.KNIGHT:
                        score -= KNIGHT_TABLE[square]

    # Mobility bonus
    score += len(list(board.legal_moves)) * 5
    return score


def minimax(board: chess.Board, depth: int, alpha: float, beta: float, maximizing: bool) -> float:
    """Alpha-beta pruning minimax search."""
    if depth == 0 or board.is_game_over():
        return evaluate_board(board)

    if maximizing:
        max_eval = float("-inf")
        for move in board.legal_moves:
            board.push(move)
            eval_score = minimax(board, depth - 1, alpha, beta, False)
            board.pop()
            max_eval = max(max_eval, eval_score)
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break
        return max_eval
    else:
        min_eval = float("inf")
        for move in board.legal_moves:
            board.push(move)
            eval_score = minimax(board, depth - 1, alpha, beta, True)
            board.pop()
            min_eval = min(min_eval, eval_score)
            beta = min(beta, eval_score)
            if beta <= alpha:
                break
        return min_eval


def find_best_move(board: chess.Board, depth: int = 3) -> chess.Move | None:
    """Find the best move for the current position."""
    best_move = None
    best_value = float("-inf") if board.turn else float("inf")
    moves = list(board.legal_moves)

    # Sort moves for better pruning (captures first)
    def capture_priority(move):
        if board.is_capture(move):
            return -1
        return 0

    moves.sort(key=capture_priority)

    for move in moves:
        board.push(move)
        value = minimax(board, depth - 1, float("-inf"), float("inf"), not board.turn)
        board.pop()

        if board.turn:  # White (maximizing)
            if value > best_value:
                best_value = value
                best_move = move
        else:  # Black (minimizing)
            if value < best_value:
                best_value = value
                best_move = move

    return best_move


def get_ai_move(fen: str) -> dict:
    """Get AI move for a FEN position. Returns dict with move or error."""
    try:
        board = chess.Board(fen)
        if board.is_game_over():
            return {"error": "game_over"}
        move = find_best_move(board, depth=3)
        if move:
            return {"from": chess.square_name(move.from_square), "to": chess.square_name(move.to_square), "fen": board.fen()}
        return {"error": "no_move"}
    except Exception as e:
        logger.error(f"AI error: {e}")
        return {"error": str(e)}
```

**Step 1:** Create the file.

**Step 2:** Run `cd /home/silvio/projects/game-hub-python && python3 -c "from core.chess_ai import get_ai_move; r = get_ai_move('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'); print(r)"` — expected: dict with `from`, `to`, `fen`

---

## Phase 6: API Routes

### Task 11: Create players routes

**Files:**
- Create: `/home/silvio/projects/game-hub-python/web/routes/players.py`

```python
"""Player management routes."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import login_player, hash_pin, verify_pin, validate_pin
from core.db import Player, get_session

router = APIRouter(prefix="/api", tags=["players"])


class LoginRequest(BaseModel):
    name: str
    pin: str


class ResetPinRequest(BaseModel):
    name: str


@router.get("/players")
async def get_players(session: AsyncSession = Depends(get_session)):
    """Get all players as a dict keyed by name."""
    result = await session.execute(select(Player))
    players = {}
    for p in result.scalars().all():
        game_wins = p.game_wins if isinstance(p.game_wins, dict) else {}
        players[p.name] = {
            "name": p.name,
            "wins": p.wins,
            "losses": p.losses,
            "gameWins": game_wins,
            "selfie": p.selfie,
            "hasPin": bool(p.pin_hash),
        }
    return players


@router.post("/login")
async def login(data: LoginRequest, session: AsyncSession = Depends(get_session)):
    """Login or set PIN for a player."""
    success, message = await login_player(session, data.name, data.pin)
    if success:
        return {"success": True, "message": message}
    raise HTTPException(status_code=401 if "Incorrect" in message else 400, detail=message)


@router.post("/api/admin/reset-pin")
async def reset_pin(data: ResetPinRequest, session: AsyncSession = Depends(get_session)):
    """Reset a player's PIN (allows re-setup on next login)."""
    result = await session.execute(select(Player).where(Player.name == data.name))
    player = result.scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    player.pin_hash = None
    await session.commit()
    return {"success": True, "message": f"PIN reset for {data.name}"}
```

---

### Task 12: Create tasks routes

**Files:**
- Create: `/home/silvio/projects/game-hub-python/web/routes/tasks.py`

```python
"""Task and reward management routes."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import Task, Transaction, Player, get_session

router = APIRouter(prefix="/api", tags=["tasks"])


class TaskCreate(BaseModel):
    child_name: str
    task_description: str
    points: int = 1
    is_recurring: bool = False
    series_total: int = 1


class TaskUpdate(BaseModel):
    is_completed: bool | None = None
    is_approved: bool | None = None
    series_count: int | None = None


class TransactionCreate(BaseModel):
    child_name: str
    amount: float
    description: str | None = None


VALID_CHILDREN = {"Emma", "Mateo", "Dad"}


@router.get("/tasks/{child}")
async def get_tasks(child: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Task).where(Task.child_name == child).order_by(Task.created_at.desc())
    )
    return result.scalars().all()


@router.post("/tasks")
async def create_task(data: TaskCreate, session: AsyncSession = Depends(get_session)):
    if data.child_name not in VALID_CHILDREN:
        raise HTTPException(status_code=400, detail="Invalid child_name")
    if not data.task_description or len(data.task_description) > 500:
        raise HTTPException(status_code=400, detail="Invalid task_description")
    task = Task(
        child_name=data.child_name,
        task_description=data.task_description.strip(),
        points=data.points,
        is_recurring=data.is_recurring,
        series_total=data.series_total,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.patch("/tasks/{task_id}")
async def update_task(task_id: int, data: TaskUpdate, session: AsyncSession = Depends(get_session)):
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if data.is_approved is not None:
        task.is_approved = data.is_approved
    elif data.series_count is not None:
        if task.is_recurring and task.last_increment_at:
            last = task.last_increment_at
            now = datetime.utcnow()
            if last.date() == now.date():
                raise HTTPException(status_code=403, detail="Only 1 event per day for recurring tasks")
        task.series_count = data.series_count
        task.is_completed = data.series_count >= task.series_total
        task.is_approved = False
        task.last_increment_at = datetime.utcnow()
    elif data.is_completed is not None:
        task.is_completed = data.is_completed
        task.is_approved = False

    await session.commit()
    await session.refresh(task)
    return task


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, session: AsyncSession = Depends(get_session)):
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await session.delete(task)
    await session.commit()
    return {"success": True}


@router.get("/transactions/{child}")
async def get_transactions(child: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Transaction).where(Transaction.child_name == child).order_by(Transaction.created_at.desc())
    )
    return result.scalars().all()


@router.post("/transactions")
async def create_transaction(data: TransactionCreate, session: AsyncSession = Depends(get_session)):
    tx = Transaction(
        child_name=data.child_name,
        amount=data.amount,
        description=data.description,
    )
    session.add(tx)
    await session.commit()
    await session.refresh(tx)
    return tx


@router.post("/payout/{child}")
async def payout(child: str, session: AsyncSession = Depends(get_session)):
    """Mark completed+approved tasks as paid and clear transactions."""
    await session.execute(
        update(Task).where(
            Task.child_name == child,
            Task.is_completed == True,
            Task.is_approved == True,
            Task.is_paid == False,
        ).values(is_paid=True)
    )
    await session.execute(
        update(Transaction).where(Transaction.child_name == child).delete()
    )
    await session.commit()
    return {"success": True}
```

---

## Phase 7: Socket.io Events

### Task 13: Create socket events handler

**Files:**
- Create: `/home/silvio/projects/game-hub-python/web/socket_events.py`

```python
"""Socket.io event handlers for real-time game communication."""

import asyncio
import logging

import socketio

from core.game_manager import game_manager
from core.chess_ai import get_ai_move
from core.db import Player, get_session
from sqlalchemy import select, update, text

logger = logging.getLogger(__name__)

sio: socketio.AsyncServer | None = None


def init_socket(sio_instance: socketio.AsyncServer):
    global sio
    sio = sio_instance


@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")


@sio.event
async def disconnect(sid):
    player_name = game_manager.remove_online(sid)
    logger.info(f"Client disconnected: {sid} ({player_name})")
    if sio:
        await sio.emit("updateOnlineStatus", game_manager.get_online_status())


@sio.event
async def login(sid, player_name: str):
    game_manager.set_online(sid, player_name)
    if sio:
        await sio.emit("updateOnlineStatus", game_manager.get_online_status() + ["Calypso"])


@sio.event
async def getOnlineUsers(sid):
    if sio:
        await sio.emit("onlineUsersResult", game_manager.get_online_status() + ["Calypso"])


@sio.event
async def getPlayers(sid):
    async for session in get_session().__anext__():
        result = await session.execute(select(Player))
        players = {}
        for p in result.scalars().all():
            game_wins = p.game_wins if isinstance(p.game_wins, dict) else {}
            players[p.name] = {
                "name": p.name, "wins": p.wins, "losses": p.losses,
                "gameWins": game_wins, "selfie": p.selfie, "hasPin": bool(p.pin_hash),
            }
        if sio:
            await sio.emit("playersResult", players)
        break


@sio.event
async def sendChallenge(sid, data: dict):
    challenger = data.get("challenger")
    opponent = data.get("opponent")
    game = data.get("game")
    logger.info(f"{challenger} challenged {opponent} to {game}")

    # Find opponent's socket and emit
    for socket_id, name in game_manager.online_users.items():
        if name == opponent and sio:
            await sio.emit("receiveChallenge", {"challenger": challenger, "game": game}, to=socket_id)
            break


@sio.event
async def acceptChallenge(sid, data: dict):
    challenger = data.get("challenger")
    opponent = data.get("opponent")
    game = data.get("game")
    room_id = f"{game}_{challenger}_{opponent}_{int(asyncio.get_event_loop().time())}"

    # Emit gameStarted to both players
    if sio:
        for socket_id, name in game_manager.online_users.items():
            if name == challenger:
                await sio.emit("gameStarted", {"roomId": room_id, "opponent": opponent, "game": game, "role": "X"}, to=socket_id)
            elif name == opponent:
                await sio.emit("gameStarted", {"roomId": room_id, "opponent": challenger, "game": game, "role": "O"}, to=socket_id)


@sio.event
async def joinRoom(sid, room_id: str):
    if sio:
        await sio.enter_room(sid, room_id)
    logger.info(f"Socket {sid} joined room {room_id}")


@sio.event
async def makeMove(sid, data: dict):
    room_id = data.get("roomId")
    move = data.get("move")
    game_type = data.get("game", "unknown")
    move_type = data.get("type")

    player_name = game_manager.online_users.get(sid, "anonymous")

    if move_type == "reset":
        game_manager.reset_chess(room_id)
        if sio:
            await sio.emit("gameReset", room=room_id)
        return

    if game_type == "chess":
        import chess
        import json

        board = chess.Board(game_manager.get_game(room_id).fen if game_manager.get_game(room_id) else None)
        try:
            # Parse move (from-to format: "e2e4")
            if isinstance(move, str) and len(move) == 4:
                mv = chess.Move(
                    chess.Square(chess.parse_square(move[:2])),
                    chess.Square(chess.parse_square(move[2:])),
                )
            else:
                mv = chess.Move.from_uci(move)

            if mv in board.legal_moves:
                board.push(mv)
                fen = board.fen()
                game_manager.update_chess_fen(room_id, fen)

                if sio:
                    await sio.emit("moveMade", {"move": move, "fen": fen}, room=room_id)

                # Check for AI opponent (solo or Calypso)
                if "solo" in room_id or "Calypso" in room_id:
                    await asyncio.sleep(0.1)  # Small delay for UX
                    ai_result = get_ai_move(fen)
                    if "error" not in ai_result:
                        ai_move = f"{ai_result['from']}{ai_result['to']}"
                        board.push(chess.Move.from_uci(ai_move))
                        fen = board.fen()
                        game_manager.update_chess_fen(room_id, fen)
                        if sio:
                            await sio.emit("moveMade", {"move": ai_move, "fen": fen}, room=room_id)

        except Exception as e:
            logger.error(f"Invalid chess move: {move} — {e}")

    else:
        next_state = data.get("nextState")
        if sio:
            await sio.emit("moveMade", {"move": move, "nextState": next_state}, room=room_id)


@sio.event
async def gameEnd(sid, data: dict):
    winner = data.get("winner")
    loser = data.get("loser")
    game = data.get("game")

    if not winner or not game:
        return

    async for session in get_session().__anext__():
        # Update winner stats
        result = await session.execute(select(Player).where(Player.name == winner))
        winner_player = result.scalar_one_or_none()
        if winner_player:
            game_wins = dict(winner_player.game_wins) if isinstance(winner_player.game_wins, dict) else {}
            game_wins[game] = game_wins.get(game, 0) + 1
            winner_player.wins += 1
            winner_player.game_wins = game_wins

        # Update loser stats
        if loser:
            result = await session.execute(select(Player).where(Player.name == loser))
            loser_player = result.scalar_one_or_none()
            if loser_player:
                loser_player.losses += 1

        await session.commit()

        # Broadcast updated players list
        if sio:
            result = await session.execute(select(Player))
            players = {}
            for p in result.scalars().all():
                game_wins = p.game_wins if isinstance(p.game_wins, dict) else {}
                players[p.name] = {"name": p.name, "wins": p.wins, "losses": p.losses, "gameWins": game_wins}
            await sio.emit("updatePlayers", players)
        break
```

---

## Phase 8: HTMX Dashboard Pages

### Task 14: Create base template and dashboard

**Files:**
- Create: `/home/silvio/projects/game-hub-python/web/templates/base.html`
- Create: `/home/silvio/projects/game-hub-python/web/templates/dashboard.html`

Reference the silrod-core base.html pattern for cross-app nav bar, but tailored for game-hub (games, leaderboard, task hub). Include:
- `/static/silrod/css/silrod.css` for shared mobile/typography CSS
- HTMX script tag
- Socket.io client script
- Game board CSS

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{% block title %}Game Hub{% endblock %}</title>
    <script src="https://unpkg.com/htmx.org@1.9.12"></script>
    <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.6.3/css/all.min.css" rel="stylesheet" />
    <link rel="stylesheet" href="/static/theme.css" />
    <link rel="stylesheet" href="/static/silrod/css/silrod.css" />
    <script src="/static/theme.js"></script>
    <style>
        body { font-family: 'Inter', sans-serif; }
        .game-board td { width: 60px; height: 60px; text-align: center; }
        .game-board td:hover { background: #f1f5f9; cursor: pointer; }
        .piece { font-size: 2rem; line-height: 1; }
        .piece.white { color: #fff; text-shadow: 0 0 2px #000; }
        .piece.black { color: #1e293b; }
        /* Bump 10px labels */
        .text-\[10px\] { font-size: 11px; }
    </style>
</head>
<body class="bg-slate-50 min-h-screen flex flex-col">
    <!-- Nav -->
    <nav class="bg-white shadow-sm border-b border-slate-200 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4">
            <div class="flex justify-between items-center h-14">
                <div class="flex items-center gap-3">
                    <span class="text-lg font-bold text-slate-800">[silrod]</span>
                    <span class="text-slate-300">|</span>
                    <span class="text-sm font-medium text-blue-600">Game Hub</span>
                </div>
                <div class="flex items-center gap-3" id="online-indicator">
                    <span class="text-xs text-slate-400">Loading...</span>
                </div>
            </div>
        </div>
    </nav>

    <main class="flex-1 max-w-7xl mx-auto w-full p-6">
        {% block content %}{% endblock %}
    </main>

    <footer class="bg-slate-800 text-white py-4 mt-auto border-t border-slate-700">
        <div class="max-w-7xl mx-auto px-4 text-center text-xs text-slate-400">
            Game Hub &copy; 2026
        </div>
    </footer>

    <script>
        // Socket.io connection
        const socket = io(window.location.origin, { transports: ["websocket"] });
        socket.on("connect", () => {
            document.getElementById("online-indicator").innerHTML =
                '<span class="text-xs text-green-600"><i class="fas fa-circle text-green-500"></i> Online</span>';
        });
        socket.on("disconnect", () => {
            document.getElementById("online-indicator").innerHTML =
                '<span class="text-xs text-slate-400">Offline</span>';
        });
    </script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

---

## Phase 9: Game HTML Pages (Vanilla JS + Socket.io)

### Task 15: Create game board templates with vanilla JS

**Files:**
- Create: `/home/silvio/projects/game-hub-python/web/templates/game/chess.html`
- Create: `/home/silvio/projects/game-hub-python/web/templates/game/tictactoe.html`

Chess page should have:
- HTML chess board (8x8 grid with Unicode pieces ♔♕♖ etc.)
- Socket.io listeners for `moveMade`, `gameReset`, `gameStarted`
- Local chess.js logic (or just use python-chess FEN updates to re-render board)
- Move input via click-to-select, click-to-place
- AI vs player flow

Tic-tac-toe page:
- 3x3 grid with X/O state
- Socket.io listeners for `moveMade`
- Click handler for cell selection
- Win/draw detection

---

### Task 16: Create static game.js client

**Files:**
- Create: `/home/silvio/projects/game-hub-python/web/static/game.js`

```javascript
// Shared game client utilities

// Render chess board from FEN
function renderChessBoard(fen, boardEl) {
    const board = fen.split(' ')[0];
    const rows = board.split('/');
    const files = 'abcdefgh';
    let html = '<table class="game-board w-full"><tbody>';
    for (let r = 0; r < 8; r++) {
        html += '<tr>';
        for (let f = 0; f < 8; f++) {
            const piece = rows[7 - r][f];
            const isWhite = piece === piece.toUpperCase();
            const cls = (r + f) % 2 === 0 ? 'bg-slate-100' : 'bg-slate-300';
            const pieceChar = pieceMap[piece.toLowerCase()] || '';
            const colorClass = isWhite ? 'white' : 'black';
            html += `<td class="${cls}" data-square="${files[f]}${8-r}">
                <span class="piece ${colorClass}">${pieceChar}</span>
            </td>`;
        }
        html += '</tr>';
    }
    html += '</tbody></table>';
    boardEl.innerHTML = html;
}

const pieceMap = {
    'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚', 'p': '♟',
    'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔', 'P': '♙',
};

// Tic-tac-toe cell handler
function initTicTacToe(boardEl, roomId, role) {
    let currentPlayer = 'X';
    let board = Array(9).fill('');

    boardEl.addEventListener('click', (e) => {
        const cell = e.target.closest('[data-cell]');
        if (!cell || cell.textContent) return;

        const idx = parseInt(cell.dataset.cell);
        board[idx] = currentPlayer;
        cell.textContent = currentPlayer;
        cell.classList.remove('text-slate-400');
        cell.classList.add(currentPlayer === 'X' ? 'text-blue-600' : 'text-red-600');

        socket.emit('makeMove', { roomId, move: idx, nextState: board, game: 'tictactoe' });

        // Check win
        const wins = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];
        for (const [a,b,c] of wins) {
            if (board[a] && board[a] === board[b] && board[a] === board[c]) {
                boardEl.querySelector(`[data-cell="${a}"]`).classList.add('bg-green-200');
                boardEl.querySelector(`[data-cell="${b}"]`).classList.add('bg-green-200');
                boardEl.querySelector(`[data-cell="${c}"]`).classList.add('bg-green-200');
            }
        }

        currentPlayer = currentPlayer === 'X' ? 'O' : 'X';
    });
}
```

---

## Phase 10: Wiring up routes and deploying

### Task 17: Wire all routes in main.py

Update `main.py` to include all routers and Socket.io setup:

```python
# In main.py after sio init
from web.routes import players, tasks
from web import socket_events

app.include_router(players.router)
app.include_router(tasks.router)

socket_events.init_socket(sio)

# Mount static
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Try silrod-core static
try:
    from silrod_ui import get_static_dir
    import os
    silrod_static = get_static_dir()
    if os.path.exists(silrod_static):
        app.mount("/static/silrod", StaticFiles(directory=silrod_static), name="silrod-static")
except ImportError:
    pass
```

---

### Task 18: Build and test Docker image

**Step 1:** Run `cd /home/silvio/projects/game-hub-python && docker build -t game-hub:0.1.0 .`

**Step 2:** Verify no build errors.

---

## Key Implementation Notes

1. **Socket.io runs as ASGI app** — `socketio.ASGIApp(sio, app)` mounts the Socket.io server alongside FastAPI on the same port.

2. **FEN state for chess** — Board rendered from FEN string. Each move updates FEN, re-renders. No client-side chess.js needed — Python chess handles logic, client just renders Unicode pieces.

3. **AI moves are blocking** — The `get_ai_move()` function uses minimax with depth=3. For a real-time experience, consider running the AI calculation in a thread pool executor so it doesn't block the async event loop.

4. **Online presence** — `game_manager.online_users` tracks socket_id → player_name. Broadcast on connect/disconnect.

5. **Rate limiting** — `GameManager.check_rate_limit()` uses in-memory store with TTL cleanup.

6. **Game cleanup** — Stale games (24h no activity) cleaned up every hour by background task.

7. **silrod-core for shared CSS** — The `/static/silrod/css/silrod.css` link in templates will serve the shared mobile/typography CSS once silrod-core is mounted.

8. **No React** — Game boards are pure HTML/CSS with vanilla JS event handlers. Socket.io handles real-time state sync. Each game page is self-contained.

---

## Verification Steps

After each task:
1. Run `python3 -c "from module import *" ` to verify imports
2. Check Docker build succeeds
3. Check health endpoint `curl http://localhost:3001/health`

After full implementation:
1. Login with `Dad` and PIN `1234`
2. Verify leaderboard loads at `GET /`
3. Create a task for `Emma`
4. Connect two browser tabs, challenge between them
5. Play a chess game, verify moves sync
6. Check mobile viewport at 375px
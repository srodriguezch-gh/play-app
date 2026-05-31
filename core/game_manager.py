"""In-memory state for active game sessions and online players."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class GameInstance:
    room_id: str
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    last_updated: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


from core.chess_game import ChessGame as _ChessGameLogic

class ChessGameInstance(GameInstance):
    """Server-side chess session with authoritative board."""
    def __init__(self, room_id: str):
        super().__init__(room_id=room_id)
        self.chess = _ChessGameLogic()


class GameManager:
    """Owns ephemeral room state, online users, and rate limits."""

    def __init__(self):
        self.games: dict[str, GameInstance] = {}
        self.online_users: dict[str, str] = {}
        self.rate_limit_store: dict[str, dict] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._rate_limit_cleanup_task: asyncio.Task | None = None

    def cleanup(self):
        """Start background cleanup tasks when an event loop is available."""
        if self._cleanup_task is None:
            try:
                loop = asyncio.get_running_loop()
                self._cleanup_task = loop.create_task(self._cleanup_loop())
                self._rate_limit_cleanup_task = loop.create_task(self._rate_limit_cleanup_loop())
            except RuntimeError:
                pass

    async def _cleanup_loop(self):
        while True:
            await asyncio.sleep(3600)
            self._cleanup_stale_games()
            self._cleanup_rate_limit()

    async def _cleanup_stale_games(self):
        now = datetime.now(timezone.utc).timestamp()
        expiry = 24 * 3600
        cleaned = 0
        for room_id in list(self.games.keys()):
            if now - self.games[room_id].last_updated > expiry:
                del self.games[room_id]
                cleaned += 1
        if cleaned:
            logger.info(f"Cleaned up {cleaned} stale game(s)")

    async def _rate_limit_cleanup_loop(self):
        while True:
            await asyncio.sleep(300)
            self._cleanup_rate_limit()

    def _cleanup_rate_limit(self):
        now = datetime.now(timezone.utc).timestamp() * 1000
        expired = [k for k, v in self.rate_limit_store.items() if now - v["window_start"] > 120000]
        for k in expired:
            self.rate_limit_store.pop(k, None)
        if expired:
            logger.debug(f"Cleaned up {len(expired)} rate limit entries")

    def set_online(self, socket_id: str, player_name: str):
        self.online_users[socket_id] = player_name

    def remove_online(self, socket_id: str) -> Optional[str]:
        return self.online_users.pop(socket_id, None)

    def get_online_status(self) -> list[str]:
        return list(self.online_users.values())

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

    def get_or_create_chess(self, room_id: str) -> ChessGameInstance:
        """Get the chess session for a room, or create a fresh one."""
        if room_id not in self.games:
            self.games[room_id] = ChessGameInstance(room_id=room_id)
        elif not isinstance(self.games[room_id], ChessGameInstance):
            self.games[room_id] = ChessGameInstance(room_id=room_id)
        game = self.games[room_id]
        game.last_updated = datetime.now(timezone.utc).timestamp()
        return game

    def update_chess_fen(self, room_id: str, fen: str):
        """Load a specific FEN into a chess room."""
        game = self.get_or_create_chess(room_id)
        game.chess.from_fen(fen)

    def reset_chess(self, room_id: str):
        """Reset a chess room to the starting position."""
        if room_id in self.games:
            self.games[room_id] = ChessGameInstance(room_id=room_id)

    def get_game(self, room_id: str) -> Optional[GameInstance]:
        return self.games.get(room_id)

    def delete_game(self, room_id: str):
        self.games.pop(room_id, None)


game_manager = GameManager()

"""Brain sync service for play-app — save/load game state to brain-app."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

BRAIN_API = os.environ.get("BRAIN_API_URL", "http://brain-app:5050")


async def save_game_result(player_name: str, game: str, winner: str, loser: str, room_id: str) -> None:
    """Save game result to brain after game completion."""
    payload = {
        "content": f"{player_name} won a {game} game against {loser} (room: {room_id}).",
        "summary": f"{player_name} beat {loser} at {game}",
        "memory_type": "event",
        "wing": "play",
        "room": "games",
        "tags": ["game", game, "win", player_name],
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(f"{BRAIN_API}/api/v1/memories", json=payload)
            logger.info(f"[Brain] Game result saved: {player_name} won {game}")
    except Exception as e:
        logger.warning(f"[Brain] Failed to save game result: {e}")


async def load_brain_game_context(player_name: str) -> dict | None:
    """Load recent game context from brain for a player."""
    query = f"{player_name} game win chess tictactoe"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{BRAIN_API}/api/v1/remember",
                json={"query": query, "limit": 5},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("results", [])
    except Exception as e:
        logger.warning(f"[Brain] Failed to load game context: {e}")
    return None
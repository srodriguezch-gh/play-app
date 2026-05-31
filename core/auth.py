"""PIN-based authentication for Play."""

import time
import re
import secrets
from typing import Optional

import bcrypt
from sqlalchemy import select

from core.db import Player, async_session


PIN_PATTERN = re.compile(r"^\d{4}$")
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 300


_rate_limit_store: dict[str, dict] = {}


def hash_pin(pin: str) -> str:
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()


def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    if not hashed_pin:
        return False
    try:
        return bcrypt.checkpw(plain_pin.encode(), hashed_pin.encode())
    except Exception:
        return False


def validate_pin(pin: str) -> tuple[bool, str]:
    if not pin or not isinstance(pin, str):
        return False, "PIN is required"
    if not PIN_PATTERN.match(pin):
        return False, "PIN must be exactly 4 digits"
    return True, ""


def _check_rate_limit(player_name: str, ip: str) -> tuple[bool, str]:
    """Return (allowed, message). Locks out after MAX_LOGIN_ATTEMPTS in LOCKOUT_SECONDS."""
    now = time.monotonic()
    key = f"{player_name}:{ip}"

    if key in _rate_limit_store:
        record = _rate_limit_store[key]
        if now - record["window_start"] > LOCKOUT_SECONDS:
            del _rate_limit_store[key]
        elif record["attempts"] >= MAX_LOGIN_ATTEMPTS:
            remaining = int(LOCKOUT_SECONDS - (now - record["window_start"]))
            return False, f"Locked out. Try again in {remaining}s"
        else:
            record["attempts"] += 1
            record["last_attempt"] = now
            return True, ""
    else:
        _rate_limit_store[key] = {
            "attempts": 1,
            "window_start": now,
            "last_attempt": now,
        }
        return True, ""


def _clear_rate_limit(player_name: str, ip: str) -> None:
    key = f"{player_name}:{ip}"
    _rate_limit_store.pop(key, None)


async def authenticate_player(name: str, pin: str, ip: str = "unknown") -> tuple[bool, str]:
    """Returns (success, message). Checks rate limit + PIN."""
    allowed, msg = _check_rate_limit(name, ip)
    if not allowed:
        return False, msg

    async with async_session() as session:
        result = await session.execute(select(Player).where(Player.name == name))
        player = result.scalar_one_or_none()

        if not player:
            _clear_rate_limit(name, ip)
            return False, "Player not found"

        if not player.pin:
            valid, msg = validate_pin(pin)
            if not valid:
                return False, msg
            player.pin = hash_pin(pin)
            await session.commit()
            _clear_rate_limit(name, ip)
            return True, f"PIN set for {name}"

        if verify_pin(pin, player.pin):
            _clear_rate_limit(name, ip)
            return True, "Authenticated"

        return False, "Incorrect PIN"


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)

"""Player management routes for Play."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import Player, Wallet, get_session

router = APIRouter(prefix="/api", tags=["players"])


class ResetPinRequest(BaseModel):
    name: str


@router.get("/players")
async def get_players(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Player))
    wallet_result = await session.execute(select(Wallet))
    wallets = {w.player_name: float(w.balance or 0) for w in wallet_result.scalars().all()}
    players = {}
    for p in result.scalars().all():
        game_wins = p.game_wins if isinstance(p.game_wins, dict) else {}
        players[p.name] = {
            "name": p.name,
            "wins": p.wins,
            "losses": p.losses,
            "balance": wallets.get(p.name, 0),
            "gameWins": game_wins,
            "selfie": p.selfie,
            "hasPin": bool(p.pin),
        }
    return players


@router.post("/admin/reset-pin")
async def reset_pin(data: ResetPinRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Player).where(Player.name == data.name))
    player = result.scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    player.pin = None
    await session.commit()
    return {"success": True, "message": f"PIN reset for {data.name}"}


@router.get("/wallet/{name}")
async def get_wallet(name: str, session: AsyncSession = Depends(get_session)):
    wallet = await session.get(Wallet, name)
    return {"name": name, "balance": float(wallet.balance or 0) if wallet else 0.0}

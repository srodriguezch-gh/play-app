"""Initialize the game-hub database and seed default players."""

import asyncio
import logging

from sqlalchemy import select

from core.auth import hash_pin
from core.db import Base, Player, Wallet, engine, async_session

logger = logging.getLogger(__name__)

DEFAULT_PLAYERS = ("Emma", "Mateo", "Dad")


async def create_schema() -> None:
    """Create tables and seed default players once."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        for name in DEFAULT_PLAYERS:
            result = await session.execute(select(Player).where(Player.name == name))
            if result.scalar_one_or_none() is None:
                session.add(
                    Player(
                        name=name,
                        pin=hash_pin("0000") if name != "Dad" else "",
                        selfie=name != "Dad",
                        wins=0,
                        losses=0,
                        game_wins={},
                    )
                )
            wallet_result = await session.execute(select(Wallet).where(Wallet.player_name == name))
            if wallet_result.scalar_one_or_none() is None:
                session.add(Wallet(player_name=name, balance=0))
        await session.commit()

    logger.info("Game-hub database initialized")


def main() -> None:
    """Run the bootstrap job."""
    asyncio.run(create_schema())


if __name__ == "__main__":
    main()

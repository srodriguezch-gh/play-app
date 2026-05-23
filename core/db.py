"""SQLAlchemy models for game-hub."""

from datetime import datetime

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

    name = Column(String(100), primary_key=True)
    pin = Column(Text, nullable=True)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    game_wins = Column(JSON, default=dict)
    selfie = Column(Text, nullable=True)


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


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True)
    platform = Column(String(50), nullable=False)  # 'steam', 'epic'
    game_id = Column(String(100), nullable=False)
    achievement_id = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    achieved = Column(Boolean, default=False)
    timestamp = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_platform_game_achievement", "platform", "game_id", "achievement_id", unique=True),
    )


async def init_db():
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with async_session() as session:
        yield session
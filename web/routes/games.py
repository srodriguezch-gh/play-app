"""Game routes for all playable games."""

import asyncio
import logging
import random
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, field_validator

from core.chess_game import ChessGame
from core.connectfour_game import ConnectFourGame
from core.hangman_game import HangmanGame
from core.rps_game import RPSGame
from core.simon_game import SimonSaysGame
from core.snake_game import SnakeGame
from core.tictactoe_game import TicTacToeGame
from core.wordsearch_game import WordSearchGame

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/games", tags=["games"])


class ChessMoveRequest(BaseModel):
    room_id: str
    move: str


class TicTacToeMoveRequest(BaseModel):
    room_id: str
    cell: int
    player: str


class RPSMoveRequest(BaseModel):
    move: str

    @field_validator("move")
    @classmethod
    def validate_move(cls, v: str) -> str:
        v = v.lower()
        if v not in {"rock", "paper", "scissors"}:
            raise ValueError("move must be rock, paper, or scissors")
        return v


class ConnectFourMoveRequest(BaseModel):
    room_id: str
    col: int
    player: str


class SnakeScoreRequest(BaseModel):
    player: str
    score: int


class HangmanGuessRequest(BaseModel):
    session_id: str
    letter: str


class WordSearchFindRequest(BaseModel):
    session_id: str
    word: str


class SimonPlayRequest(BaseModel):
    session_id: str
    color: str


class SimonNextRoundRequest(BaseModel):
    session_id: str


# ---------------------------------------------------------------------------
# TTL-cached game state — prevents unbounded memory growth
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[float, object]] = {}


def _cache_set(key: str, value: object, ttl: int = 3600) -> None:
    _cache[key] = (time.monotonic() + ttl, value)


def _cache_get(key: str) -> object | None:
    entry = _cache.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.monotonic() > expires_at:
        _cache.pop(key, None)
        return None
    return value


def _cache_cleanup() -> None:
    now = time.monotonic()
    expired = [k for k, (exp, _) in _cache.items() if now > exp]
    for k in expired:
        _cache.pop(k, None)


async def _periodic_cache_cleanup() -> None:
    while True:
        await asyncio.sleep(300)
        _cache_cleanup()


asyncio.create_task(_periodic_cache_cleanup())

# ---------------------------------------------------------------------------
# Chess
# ---------------------------------------------------------------------------


@router.post("/chess/move")
async def chess_move(data: ChessMoveRequest):
    from core.game_manager import game_manager as _gm

    game = _gm.get_or_create_chess(data.room_id)
    success = game.chess.move(data.move)
    if not success:
        raise HTTPException(status_code=400, detail="Illegal chess move")
    return {
        "fen": game.chess.to_fen(),
        "legal": game.chess.get_legal_moves(),
        "game_over": game.chess.is_game_over(),
        "winner": game.chess.get_winner(),
    }


@router.post("/chess/reset")
async def chess_reset(room_id: str = Query(...)):
    from core.game_manager import game_manager as _gm

    _gm.reset_chess(room_id)
    return {"status": "reset"}


# ---------------------------------------------------------------------------
# Tic-Tac-Toe
# ---------------------------------------------------------------------------


@router.post("/tictactoe/move")
async def tictactoe_move(data: TicTacToeMoveRequest):
    from core.game_manager import game_manager as _gm

    game = _gm.get_or_create_tictactoe(data.room_id)
    success = game.tictactoe.move(data.cell, data.player)
    if not success:
        raise HTTPException(status_code=400, detail="Illegal tic-tac-toe move")
    return {
        "board": game.tictactoe.get_board(),
        "game_over": game.tictactoe.is_game_over(),
        "winner": game.tictactoe.get_winner(),
    }


# ---------------------------------------------------------------------------
# Rock Paper Scissors
# ---------------------------------------------------------------------------


@router.post("/rps/play")
async def rps_play(data: RPSMoveRequest):
    choices = ["rock", "paper", "scissors"]
    opponent_move = random.choice(choices)
    game = RPSGame()
    winner = game.play(data.move, opponent_move)
    return {"winner": winner, "your_move": data.move, "bot_move": opponent_move}


# ---------------------------------------------------------------------------
# Connect Four
# ---------------------------------------------------------------------------


@router.post("/connectfour/move")
async def connectfour_move(data: ConnectFourMoveRequest):
    from core.game_manager import game_manager as _gm

    game = _gm.get_or_create_connectfour(data.room_id)
    success = game.connectfour.move(data.col, data.player)
    if not success:
        raise HTTPException(status_code=400, detail="Illegal Connect Four move")
    return {
        "board": game.connectfour.get_board(),
        "game_over": game.connectfour.is_game_over(),
        "winner": game.connectfour.get_winner(),
    }


# ---------------------------------------------------------------------------
# Snake
# ---------------------------------------------------------------------------


@router.post("/snake/score")
async def snake_score(data: SnakeScoreRequest):
    game = SnakeGame()
    game.submit_score(data.score)
    return {"high_score": game.score}


# ---------------------------------------------------------------------------
# Hangman
# ---------------------------------------------------------------------------


@router.post("/hangman/start")
async def hangman_start(session_id: str = Query(...)):
    _cache_set(f"hangman:{session_id}", HangmanGame(), ttl=1800)
    game = _cache_get(f"hangman:{session_id}")
    return {"visible": game.visible, "lives": game.lives}


@router.post("/hangman/guess")
async def hangman_guess(data: HangmanGuessRequest):
    game = _cache_get(f"hangman:{data.session_id}")
    if not game:
        game = HangmanGame()
        _cache_set(f"hangman:{data.session_id}", game, ttl=1800)
    game.guess(data.letter)
    return {
        "visible": getattr(game, "visible", ""),
        "lives": getattr(game, "lives", 0),
        "game_over": getattr(game, "is_game_over", True),
        "won": getattr(game, "has_won", False),
    }


# ---------------------------------------------------------------------------
# Word Search
# ---------------------------------------------------------------------------


@router.post("/wordsearch/start")
async def wordsearch_start(session_id: str = Query(...)):
    game = WordSearchGame()
    _cache_set(f"wordsearch:{session_id}", game, ttl=1800)
    return {"grid": game.get_grid()}


@router.post("/wordsearch/find")
async def wordsearch_find(data: WordSearchFindRequest):
    game = _cache_get(f"wordsearch:{data.session_id}")
    if not game:
        raise HTTPException(status_code=404, detail="Session not found — start a game first")
    result = game.submit_word(data.word)
    if result["success"]:
        return {"found": data.word, "score": result["score"], "game_over": game.is_game_over}
    return {"message": result["message"], "score": result["score"], "game_over": game.is_game_over}


# ---------------------------------------------------------------------------
# Simon Says
# ---------------------------------------------------------------------------


@router.post("/simon/start")
async def simon_start(session_id: str = Query(...)):
    game = SimonSaysGame()
    game.reset()
    _cache_set(f"simon:{session_id}", game, ttl=1800)
    return {"sequence": []}


@router.post("/simon/round")
async def simon_round(data: SimonNextRoundRequest):
    game = _cache_get(f"simon:{data.session_id}")
    if not game:
        raise HTTPException(status_code=404, detail="Session not found — start a game first")
    return {"sequence": getattr(game, "sequence", [])}


@router.post("/simon/play")
async def simon_play(data: SimonPlayRequest):
    game = _cache_get(f"simon:{data.session_id}")
    if not game:
        raise HTTPException(status_code=404, detail="Session not found")
    success = game.play(data.color)
    if not success:
        return {"success": False, "score": game.score, "game_over": True}
    return {
        "success": True,
        "score": game.score,
        "round_complete": game.is_round_complete,
        "game_over": game.is_game_over,
    }

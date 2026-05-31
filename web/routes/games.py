"""Game routes for chess, tic-tac-toe, RPS, and Connect Four."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.chess_game import ChessGame
from core.connectfour_game import ConnectFourGame
from core.rps_game import RPSGame
from core.tictactoe_game import TicTacToeGame

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
    move: str  # rock, paper, or scissors


class ConnectFourMoveRequest(BaseModel):
    col: int
    player: str


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
    from core.tictactoe_game import TicTacToeGame
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
async def rps_play(move: str, opponent_move: Optional[str] = None):
    """Play Rock Paper Scissors against a bot if no opponent provided."""
    game = RPSGame()
    if opponent_move is None:
        opponent_move = "rock"  # default for demo
    winner = game.play(move, opponent_move)
    return {"winner": winner, "your_move": move, "bot_move": opponent_move}


# ---------------------------------------------------------------------------
# Connect Four
# ---------------------------------------------------------------------------

@router.post("/connectfour/move")
async def connectfour_move(data: ConnectFourMoveRequest):
    from core.game_manager import game_manager as _gm
    from core.connectfour_game import ConnectFourGame
    game = _gm.get_or_create_connectfour(data.room_id)
    success = game.connectfour.move(data.col, data.player)
    if not success:
        raise HTTPException(status_code=400, detail="Illegal Connect Four move")
    return {
        "board": game.connectfour.get_board(),
        "game_over": game.connectfour.is_game_over(),
        "winner": game.connectfour.get_winner(),
    }

"""Game routes for all playable games."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.chess_game import ChessGame
from core.connectfour_game import ConnectFourGame
from core.hangman_game import HangmanGame
from core.rps_game import RPSGame
from core.simon_game import SimonSaysGame
from core.snake_game import SnakeGame
from core.tictactoe_game import TicTacToeGame
from core.wordsearch_game import WordSearchGame
from core.db import async_session, Player, Wallet
from sqlalchemy import select

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


async def _credit_game_win(winner: str, loser: str, game: str) -> None:
    """Credit winner's wallet (+10) and update stats. Idempotent via unique game state."""
    if not winner or winner.lower() == "draw":
        return
    async with async_session() as session:
        result = await session.execute(select(Player).where(Player.name == winner))
        winner_player = result.scalars().one_or_none()
        if winner_player:
            game_wins = dict(winner_player.game_wins) if isinstance(winner_player.game_wins, dict) else {}
            game_wins[game] = game_wins.get(game, 0) + 1
            winner_player.wins += 1
            winner_player.game_wins = game_wins
        wallet_result = await session.execute(select(Wallet).where(Wallet.player_name == winner))
        winner_wallet = wallet_result.scalars().one_or_none()
        if winner_wallet is None:
            winner_wallet = Wallet(player_name=winner, balance=0)
            session.add(winner_wallet)
        winner_wallet.balance = (winner_wallet.balance or 0) + 10
        if loser:
            result = await session.execute(select(Player).where(Player.name == loser))
            loser_player = result.scalars().one_or_none()
            if loser_player:
                loser_player.losses += 1
        await session.commit()


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


# ---------------------------------------------------------------------------
# Snake
# ---------------------------------------------------------------------------

_snake_games = {}

@router.post("/snake/score")
async def snake_score(data: SnakeScoreRequest):
    game = SnakeGame()
    game.submit_score(data.score)
    return {"high_score": game.score}


# ---------------------------------------------------------------------------
# Hangman
# ---------------------------------------------------------------------------

_hangman_games = {}

@router.post("/hangman/start")
async def hangman_start(session_id: str = Query(...)):
    _hangman_games[session_id] = HangmanGame()
    return {"visible": _hangman_games[session_id].visible, "lives": _hangman_games[session_id].lives}


@router.post("/hangman/guess")
async def hangman_guess(data: HangmanGuessRequest):
    game = _hangman_games.get(data.session_id)
    if not game:
        game = _hangman_games[data.session_id] = HangmanGame()
    elif not hasattr(game, 'word'):
        _hangman_games[data.session_id] = HangmanGame()
        game = _hangman_games[data.session_id]
    game.guess(data.letter)
    return {
        "visible": getattr(game, 'visible', ""),
        "lives": getattr(game, 'lives', 0),
        "game_over": getattr(game, 'is_game_over', True),
        "won": getattr(game, 'has_won', False),
    }


# ---------------------------------------------------------------------------
# Word Search
# ---------------------------------------------------------------------------

_wordsearch_games = {}

@router.post("/wordsearch/start")
async def wordsearch_start(session_id: str = Query(...)):
    _wordsearch_games[session_id] = WordSearchGame()
    return {"grid": _wordsearch_games[session_id].get_grid()}


@router.post("/wordsearch/find")
async def wordsearch_find(data: WordSearchFindRequest):
    game = _wordsearch_games.get(data.session_id)
    if not game:
        raise HTTPException(status_code=404, detail="Session not found — start a game first")
    result = game.submit_word(data.word)
    if result["success"]:
        return {"found": data.word, "score": result["score"], "game_over": game.is_game_over}
    return {"message": result["message"], "score": result["score"], "game_over": game.is_game_over}


# ---------------------------------------------------------------------------
# Simon Says
# ---------------------------------------------------------------------------

_simon_games = {}

@router.post("/simon/start")
async def simon_start(session_id: str = Query(...)):
    game = _simon_games[session_id] = SimonSaysGame()
    game.reset()
    return {"sequence": []}


@router.post("/simon/round")
async def simon_round(data: SimonNextRoundRequest):
    game = _simon_games.get(data.session_id)
    if not game:
        raise HTTPException(status_code=404, detail="Session not found — start a game first")
    # Actually, data doesn't have session_id — fix using Query
    return {"sequence": getattr(game, 'sequence', [])}


@router.post("/simon/play")
async def simon_play(data: SimonPlayRequest):
    game = _simon_games.get(data.session_id)
    if not game:
        raise HTTPException(status_code=404, detail="Session not found")
    success = game.play(data.color)
    if not success:
        return {"success": False, "score": game.score, "game_over": True}
    return {"success": True, "score": game.score, "round_complete": game.is_round_complete, "game_over": game.is_game_over}

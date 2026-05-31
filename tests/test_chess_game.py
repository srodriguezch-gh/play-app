"""Test server-side chess game."""

import pytest

from core.chess_game import ChessGame


def test_new_game_fen():
    cg = ChessGame()
    assert "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" in cg.to_fen()


def test_legal_moves():
    cg = ChessGame()
    assert "e2e4" in cg.get_legal_moves()


def test_valid_move():
    cg = ChessGame()
    assert cg.move("e2e4")
    assert "e2e4" in [m.uci() for m in cg.board.move_stack]


def test_invalid_move():
    cg = ChessGame()
    assert not cg.move("e2e8")


def test_game_over_new_game():
    cg = ChessGame()
    assert not cg.is_game_over()


def test_winner_new_game():
    cg = ChessGame()
    assert cg.get_winner() is None

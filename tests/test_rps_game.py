"""Test server-side Rock Paper Scissors."""

import pytest

from core.rps_game import RPSGame


def test_draw():
    game = RPSGame()
    assert game.play("rock", "rock") == "draw"


def test_p1_wins():
    game = RPSGame()
    assert game.play("rock", "scissors") == "p1"


def test_p2_wins():
    game = RPSGame()
    assert game.play("rock", "paper") == "p2"


def test_game_over():
    game = RPSGame()
    game.play("rock", "scissors")
    assert game.is_game_over()

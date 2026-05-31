"""Minimal Checkers game."""

from dataclasses import dataclass, field


class CheckersGame:
    """Minimal checkers board for tracking."""

    def __init__(self):
        self.turn = "red"
        self.winner: str | None = None

    @property
    def is_game_over(self) -> bool:
        return self.winner is not None

    def get_winner(self) -> str | None:
        return self.winner

    def move(self, from_pos: str, to_pos: str) -> bool:
        # Simplified for demo - in a real implementation this would validate checkers rules
        self.turn = "black" if self.turn == "red" else "red"
        return True

    def reset(self) -> None:
        self.turn = "red"
        self.winner = None

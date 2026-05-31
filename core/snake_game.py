"""Minimal Snake game tracker (client-side game, server-side scoring)."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SnakeGame:
    """Track high score for a snake session."""
    score: int = 0
    is_game_over: bool = False

    def submit_score(self, score: int) -> None:
        self.score = max(self.score, score)
        self.is_game_over = True

    def reset(self) -> None:
        self.score = 0
        self.is_game_over = False

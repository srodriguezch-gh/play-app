"""Server-authoritative Rock Paper Scissors."""

import random
from dataclasses import dataclass, field


@dataclass
class RPSGame:
    """A single Rock Paper Scissors game."""

    moves: list = field(default_factory=list)

    CHOICES = {"rock", "paper", "scissors"}

    def play(self, p1_move: str, p2_move: str) -> str:
        """Returns 'p1', 'p2', or 'draw'."""
        p1_move = p1_move.lower()
        p2_move = p2_move.lower()
        if p1_move not in self.CHOICES or p2_move not in self.CHOICES:
            raise ValueError("Invalid choice")
        self.moves = [p1_move, p2_move]
        if p1_move == p2_move:
            return "draw"
        beats = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
        if beats[p1_move] == p2_move:
            return "p1"
        return "p2"

    def is_game_over(self) -> bool:
        return len(self.moves) == 2

    def get_winner(self) -> str | None:
        if not self.is_game_over():
            return None
        return self.play(self.moves[0], self.moves[1])

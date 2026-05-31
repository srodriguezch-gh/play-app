"""Minimal Simon Says game — server generates sequence, client repeats."""

import random
from dataclasses import dataclass, field


@dataclass
class SimonSaysGame:
    """Track state of a simon says game."""

    COLORS = ("red", "green", "blue", "yellow")

    sequence: list = field(default_factory=list)
    player_step: int = 0
    score: int = 0

    def next_round(self) -> None:
        self.sequence.append(random.choice(self.COLORS))
        self.player_step = 0
        self.score = len(self.sequence) - 1

    def play(self, color: str) -> bool:
        if self.player_step >= len(self.sequence):
            return False
        if self.sequence[self.player_step] != color:
            return False
        self.player_step += 1
        return True

    @property
    def is_round_complete(self) -> bool:
        return self.player_step >= len(self.sequence)

    @property
    def is_game_over(self) -> bool:
        return False  # Simon says doesn't end unless player makes a mistake

    def reset(self) -> None:
        self.sequence = []
        self.player_step = 0
        self.score = 0

"""Minimal Word Search game."""

import random
import string
from dataclasses import dataclass, field


@dataclass
class WordSearchGame:
    """Track state of a word search game."""

    SIZE = 10
    WORDS = ["PYTHON", "CHESS", "SILROD", "FAMILY", "DOCKER", "REDIS", "FASTAPI"]

    grid: list = field(default_factory=list)
    found: set = field(default_factory=set)

    def __post_init__(self):
        if not self.grid:
            self._generate_grid()

    def _generate_grid(self) -> None:
        # Initialize empty grid
        self.grid = [[""] * self.SIZE for _ in range(self.SIZE)]

        # Place words randomly
        placed = []
        for word in self.WORDS:
            placed.append(word)
            # Simple horizontal placement
            row = random.randint(0, self.SIZE - 1)
            col = random.randint(0, self.SIZE - len(word))
            for i, ch in enumerate(word):
                self.grid[row][col + i] = ch

        # Fill empty cells
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                if self.grid[r][c] == "":
                    self.grid[r][c] = random.choice(string.ascii_uppercase)

    def get_grid(self) -> list:
        return [row.copy() for row in self.grid]

    def submit_word(self, word: str) -> dict:
        word = word.upper()
        if word in self.found:
            return {"success": False, "message": "Already found"}
        if word in self.WORDS:
            self.found.add(word)
            return {"success": True, "score": len(self.found)}
        return {"success": False, "message": "Not in word list"}

    @property
    def is_game_over(self) -> bool:
        return self.found == set(self.WORDS)

    def reset(self) -> None:
        self.found.clear()
        self._generate_grid()

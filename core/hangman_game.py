"""Minimal Hangman game — server picks word, client sends guesses."""

import random
from dataclasses import dataclass, field


@dataclass
class HangmanGame:
    """Track state of a hangman game."""

    WORDS = [
        "python", "chess", "silrod", "family", "tampa", "homelab",
        "postgres", "redis", "docker", "kubernetes"
    ]

    word: str = field(default_factory=lambda: random.choice(HangmanGame.WORDS))
    guesses: set = field(default_factory=set)
    max_lives: int = 6

    @property
    def lives(self) -> int:
        wrong = [g for g in self.guesses if g not in self.word]
        return max(0, self.max_lives - len(wrong))

    @property
    def visible(self) -> str:
        return "".join(l if l in self.guesses else "_" for l in self.word)

    @property
    def is_game_over(self) -> bool:
        return self.has_won() or self.lives == 0

    def has_won(self) -> bool:
        return all(l in self.guesses for l in self.word)

    def guess(self, letter: str) -> bool:
        letter = letter.lower()
        if len(letter) != 1:
            return False
        self.guesses.add(letter)
        return True

    def reset(self) -> None:
        self.word = random.choice(self.WORDS)
        self.guesses = set()

"""Server-authoritative tic-tac-toe."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TicTacToeGame:
    """A single tic-tac-toe board with validation and win detection."""

    board: List[str] = field(default_factory=lambda: [""] * 9)
    winner: str | None = None
    moves: int = 0

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_board(self) -> list[str]:
        return self.board.copy()

    def is_game_over(self) -> bool:
        return self.winner is not None or self.moves >= 9

    def get_winner(self) -> str | None:
        return self.winner

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def move(self, cell: int, player: str) -> bool:
        if not 0 <= cell <= 8:
            return False
        if self.board[cell] != "":
            return False
        self.board[cell] = player
        self.moves += 1
        self._check_winner()
        return True

    def reset(self) -> None:
        self.board = [""] * 9
        self.winner = None
        self.moves = 0

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _check_winner(self):
        wins = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6),
        ]
        for a, b, c in wins:
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                self.winner = self.board[a]
                return

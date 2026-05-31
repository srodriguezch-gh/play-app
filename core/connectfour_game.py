"""Server-authoritative Connect Four."""

from dataclasses import dataclass, field


@dataclass
class ConnectFourGame:
    """A single Connect Four board."""

    ROWS = 6
    COLS = 7
    board: list = field(default_factory=lambda: [[""] * 7 for _ in range(6)])
    current_player: str = "red"
    winner: str | None = None

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_board(self) -> list:
        return [row.copy() for row in self.board]

    def is_game_over(self) -> bool:
        return self.winner is not None or self._is_full()

    def get_winner(self) -> str | None:
        return self.winner

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def move(self, col: int, player: str) -> bool:
        if not 0 <= col < self.COLS:
            return False
        if self.winner:
            return False
        # find lowest empty row in column
        for row in reversed(range(self.ROWS)):
            if self.board[row][col] == "":
                self.board[row][col] = player
                self._check_winner(row, col)
                self.current_player = "yellow" if player == "red" else "red"
                return True
        return False

    def reset(self) -> None:
        self.board = [[""] * self.COLS for _ in range(self.ROWS)]
        self.winner = None
        self.current_player = "red"

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _is_full(self) -> bool:
        return all(cell != "" for row in self.board for cell in row)

    def _check_winner(self, last_row: int, last_col: int):
        player = self.board[last_row][last_col]
        if not player:
            return
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            count = 1
            for step in (1, -1):
                r, c = last_row + step * dr, last_col + step * dc
                while 0 <= r < self.ROWS and 0 <= c < self.COLS and self.board[r][c] == player:
                    count += 1
                    r += step * dr
                    c += step * dc
            if count >= 4:
                self.winner = player
                return

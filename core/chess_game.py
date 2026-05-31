"""Server-authoritative chess game using python-chess."""

import chess


class ChessGame:
    """Wraps python-chess Board with simple move + status helpers."""

    def __init__(self):
        self._board = chess.Board()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def to_fen(self) -> str:
        return self._board.fen()

    @property
    def board(self) -> chess.Board:
        return self._board

    def get_legal_moves(self) -> list[str]:
        """Return all legal moves as UCI strings."""
        return [m.uci() for m in self._board.legal_moves]

    def is_game_over(self) -> bool:
        return self._board.is_game_over()

    def get_winner(self) -> str | None:
        """Return 'white', 'black', 'draw', or None."""
        if self._board.is_checkmate():
            return "white" if self._board.turn == chess.BLACK else "black"
        if self._board.is_stalemate() or self._board.is_insufficient_material() or self._board.is_fivefold_repetition() or self._board.is_seventyfive_moves():
            return "draw"
        return None

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def move(self, move_str: str) -> bool:
        """Validate and apply a UCI move. Returns True on success."""
        try:
            mv = chess.Move.from_uci(move_str)
            if mv in self._board.legal_moves:
                self._board.push(mv)
                return True
        except (ValueError, KeyError):
            pass
        return False

    def reset(self) -> None:
        self._board.reset()

    def from_fen(self, fen: str) -> None:
        self._board.set_fen(fen)

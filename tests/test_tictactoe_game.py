"""Test server-side tic-tac-toe."""

from core.tictactoe_game import TicTacToeGame


def test_new_game():
    game = TicTacToeGame()
    assert game.get_board() == [""] * 9
    assert not game.is_game_over()
    assert game.get_winner() is None


def test_valid_move():
    game = TicTacToeGame()
    assert game.move(0, "X")
    assert game.get_board()[0] == "X"


def test_invalid_move():
    game = TicTacToeGame()
    assert game.move(0, "X")
    assert not game.move(0, "O")  # occupied


def test_win_row():
    game = TicTacToeGame()
    game.move(0, "X")
    game.move(3, "O")
    game.move(1, "X")
    game.move(4, "O")
    game.move(2, "X")  # X wins top row
    assert game.get_winner() == "X"
    assert game.is_game_over()


def test_draw():
    game = TicTacToeGame()
    moves = [(0, "X"), (1, "O"), (2, "X"), (3, "O"), (4, "X"), (6, "O"), (5, "X"), (8, "O"), (7, "X")]
    for cell, player in moves:
        game.move(cell, player)
    assert game.is_game_over()
    assert game.get_winner() is None


def test_reset():
    game = TicTacToeGame()
    game.move(0, "X")
    game.reset()
    assert game.get_board() == [""] * 9
    assert not game.is_game_over()

"""Test server-side Connect Four."""

from core.connectfour_game import ConnectFourGame


def test_new_game():
    game = ConnectFourGame()
    assert game.get_board() == [[""] * 7 for _ in range(6)]
    assert not game.is_game_over()
    assert game.get_winner() is None


def test_valid_move():
    game = ConnectFourGame()
    assert game.move(0, "red")
    assert game.get_board()[5][0] == "red"


def test_invalid_move():
    game = ConnectFourGame()
    assert not game.move(7, "red")  # out of range


def test_win_horizontal():
    game = ConnectFourGame()
    for col in range(4):
        game.move(col, "red")
    assert game.get_winner() == "red"


def test_win_vertical():
    game = ConnectFourGame()
    for _ in range(4):
        game.move(0, "red")
    assert game.get_winner() == "red"


def test_draw():
    game = ConnectFourGame()
    for col in range(7):
        for row in range(6):
            player = "red" if (col + row) % 2 == 0 else "yellow"
            game.move(col, player)
    assert game.is_game_over()

from ej_boards.mommy_recipes import BoardRecipes


class TestBoardModel(BoardRecipes):
    def test_str_board(self, db, board):
        assert board.title == str(board)

    def test_get_board_absolute_url(self, db, board):
        assert board.get_absolute_url() == f'/{board.slug}/'

    def test_get_default_palette_css_class(self, db, board):
        from ej_boards.models import Board
        assert Board.get_default_css_palette() == 'bluePalette'

    def test_get_board_palette_css_class(self, db, board):
        board.palette = 'Grey'
        assert board.css_palette == 'greyPalette'

import chess
import pytest

from game import (
    GameLine,
    clear_board,
    edit_square,
    handle_play_click,
    handle_play_move,
    handle_setup_click,
    line_from_fen,
    line_from_pgn,
    position_problems,
    sanitize_castling,
    set_turn,
)


def test_line_navigation():
    line = GameLine()
    for uci in ("e2e4", "e7e5", "g1f3"):
        line.push(chess.Move.from_uci(uci))
    assert line.length == 3
    assert line.ply == 3

    line.goto(0)
    assert line.board.fen() == chess.STARTING_FEN

    line.step(2)
    assert line.ply == 2
    assert line.board.piece_at(chess.E5) == chess.Piece(chess.PAWN, chess.BLACK)

    line.step(-10)
    assert line.ply == 0
    line.step(99)
    assert line.ply == 3


def test_push_truncates_future_moves():
    line = GameLine()
    for uci in ("e2e4", "e7e5", "g1f3"):
        line.push(chess.Move.from_uci(uci))
    line.goto(1)
    line.push(chess.Move.from_uci("c7c5"))
    assert line.moves == ["e2e4", "c7c5"]
    assert line.ply == 2


def test_san_and_labels():
    line = GameLine()
    for uci in ("e2e4", "e7e5", "g1f3"):
        line.push(chess.Move.from_uci(uci))
    assert line.san_moves() == ["e4", "e5", "Nf3"]
    assert line.move_labels() == ["1.e4", "1...e5", "2.Nf3"]


def test_labels_respect_root_position():
    line = GameLine(root_fen="r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 3")
    line.push(chess.Move.from_uci("f8c5"))
    assert line.move_labels() == ["3...Bc5"]


def test_legal_move_and_promotion():
    line = GameLine(root_fen="8/4P3/8/8/8/8/8/4K2k w - - 0 1")
    move = line.legal_move(chess.E7, chess.E8, promotion=chess.KNIGHT)
    assert move is not None and move.promotion == chess.KNIGHT
    assert line.legal_move(chess.E7, chess.E5) is None


def test_undo():
    line = GameLine()
    line.push(chess.Move.from_uci("e2e4"))
    line.undo()
    assert line.moves == []
    assert line.ply == 0
    line.undo()  # não deve levantar erro
    assert line.moves == []


def test_pgn_roundtrip():
    line = GameLine()
    for uci in ("e2e4", "e7e5", "g1f3"):
        line.push(chess.Move.from_uci(uci))
    reloaded = line_from_pgn(line.to_pgn())
    assert reloaded.moves == line.moves
    assert reloaded.board.fen() == line.board.fen()


def test_pgn_with_custom_start_position():
    line = GameLine(root_fen="8/5ppp/8/3P4/8/6K1/5PPP/8 w - - 0 1")
    line.push(chess.Move.from_uci("d5d6"))
    reloaded = line_from_pgn(line.to_pgn())
    assert reloaded.root_fen == line.root_fen
    assert reloaded.moves == ["d5d6"]


def test_pgn_invalid_raises():
    with pytest.raises(ValueError):
        line_from_pgn("isto não é um pgn")


def test_line_from_fen_invalid_raises():
    with pytest.raises(ValueError):
        line_from_fen("posição inexistente")


def test_edit_square_place_and_remove():
    fen = clear_board()
    fen = edit_square(fen, chess.E4, chess.Piece(chess.KNIGHT, chess.WHITE))
    assert chess.Board(fen).piece_at(chess.E4) == chess.Piece(chess.KNIGHT, chess.WHITE)

    fen = edit_square(fen, chess.E4, None)
    assert chess.Board(fen).piece_at(chess.E4) is None


def test_edit_square_keeps_single_king():
    fen = clear_board()
    fen = edit_square(fen, chess.E1, chess.Piece(chess.KING, chess.WHITE))
    fen = edit_square(fen, chess.G1, chess.Piece(chess.KING, chess.WHITE))
    board = chess.Board(fen)
    assert len(board.pieces(chess.KING, chess.WHITE)) == 1
    assert board.piece_at(chess.G1) == chess.Piece(chess.KING, chess.WHITE)


def test_castling_rights_dropped_when_rook_removed():
    fen = edit_square(chess.STARTING_FEN, chess.H1, None)
    assert "K" not in chess.Board(fen).castling_xfen()
    assert "Q" in chess.Board(fen).castling_xfen()


def test_sanitize_castling_on_moved_king():
    board = chess.Board(chess.STARTING_FEN)
    board.remove_piece_at(chess.E1)
    board.set_piece_at(chess.G1, chess.Piece(chess.KING, chess.WHITE))
    sanitize_castling(board)
    rights = board.castling_xfen()
    assert "K" not in rights and "Q" not in rights
    assert "k" in rights and "q" in rights


def test_position_problems_detects_missing_kings():
    problems = position_problems(clear_board())
    assert len(problems) == 2


def test_position_problems_detects_pawn_on_last_rank():
    fen = edit_square("4k3/8/8/8/8/8/8/4K3 w - - 0 1", chess.A8, chess.Piece(chess.PAWN, chess.WHITE))
    assert any("fileira" in problem for problem in position_problems(fen))


def test_position_problems_ok_for_legal_position():
    assert position_problems(chess.STARTING_FEN) == []


def test_set_turn():
    fen = set_turn(chess.STARTING_FEN, chess.BLACK)
    assert chess.Board(fen).turn == chess.BLACK


def test_play_click_selects_then_moves():
    line = GameLine()
    selected = handle_play_click(line, None, chess.E2)
    assert selected == chess.E2

    selected = handle_play_click(line, selected, chess.E4)
    assert selected is None
    assert line.moves == ["e2e4"]
    assert line.board.turn == chess.BLACK

    selected = handle_play_click(line, None, chess.E7)
    assert selected == chess.E7
    selected = handle_play_click(line, selected, chess.E5)
    assert selected is None
    assert line.moves == ["e2e4", "e7e5"]
    assert line.board.turn == chess.WHITE


def test_play_click_ignores_opponent_piece():
    line = GameLine()
    assert handle_play_click(line, None, chess.E7) is None
    assert line.moves == []


def test_play_click_deselects_on_same_square():
    line = GameLine()
    assert handle_play_click(line, chess.E2, chess.E2) is None


def test_play_click_switches_selection_on_illegal_target():
    line = GameLine()
    selected = handle_play_click(line, chess.E2, chess.D2)
    assert selected == chess.D2
    assert line.moves == []


def test_play_click_cancels_on_empty_illegal_target():
    line = GameLine()
    assert handle_play_click(line, chess.E2, chess.E5) is None


def test_play_click_promotes_with_chosen_piece():
    line = GameLine(root_fen="8/4P3/8/8/8/8/8/4K2k w - - 0 1")
    handle_play_click(line, chess.E7, chess.E8, promotion=chess.ROOK)
    assert line.moves == ["e7e8r"]


def test_play_drag_moves_piece_and_switches_turn():
    line = GameLine()
    assert handle_play_move(line, chess.E2, chess.E4)
    assert line.moves == ["e2e4"]
    assert line.board.turn == chess.BLACK

    assert handle_play_move(line, chess.E7, chess.E5)
    assert line.moves == ["e2e4", "e7e5"]
    assert line.board.turn == chess.WHITE


def test_play_drag_rejects_illegal_move():
    line = GameLine()
    assert not handle_play_move(line, chess.E2, chess.E5)
    assert line.moves == []


def test_play_drag_promotes_with_chosen_piece():
    line = GameLine(root_fen="8/4P3/8/8/8/8/8/4K2k w - - 0 1")
    assert handle_play_move(line, chess.E7, chess.E8, promotion=chess.ROOK)
    assert line.moves == ["e7e8r"]


def test_setup_click_places_and_toggles_piece():
    line = GameLine(root_fen=clear_board())
    line = handle_setup_click(line, chess.E4, "N")
    assert line.board.piece_at(chess.E4) == chess.Piece(chess.KNIGHT, chess.WHITE)

    line = handle_setup_click(line, chess.E4, "N")
    assert line.board.piece_at(chess.E4) is None


def test_setup_click_eraser():
    line = GameLine()
    line = handle_setup_click(line, chess.E2, "erase")
    assert line.board.piece_at(chess.E2) is None

import chess
import pytest

from analysis import analyze_position, overall_score, render_board
from analysis.center import classify_center
from analysis.development import development_score, undeveloped_minors
from analysis.material import count_material, material_value
from analysis.pawn_majority import count_wing_pawns
from analysis.pawn_structure import analyze_structure


def test_material_balanced_at_start():
    board = chess.Board()
    white = material_value(count_material(board, chess.WHITE))
    black = material_value(count_material(board, chess.BLACK))
    assert white == black


def test_material_detects_extra_rook():
    board = chess.Board("4k3/8/8/8/8/8/8/R3K3 w - - 0 1")
    result = analyze_position(board)[0]
    assert result.score > 0
    assert any("torres" in f for f in result.findings)


def test_wing_majority_counts():
    board = chess.Board("8/pp4pp/8/8/8/8/1P4PP/8 w - - 0 1")
    white = count_wing_pawns(board, chess.WHITE)
    black = count_wing_pawns(board, chess.BLACK)
    assert white["queenside"] == 1
    assert black["queenside"] == 2
    assert white["kingside"] == 2
    assert black["kingside"] == 2


def test_development_start_position_is_zero():
    board = chess.Board()
    assert development_score(board, chess.WHITE) == 0
    assert len(undeveloped_minors(board, chess.WHITE)) == 4


def test_development_counts_castling_and_minors():
    board = chess.Board("rnbqkbnr/pppppppp/8/8/8/2N2N2/PPPPBPPP/R1BQ1RK1 w kq - 0 1")
    assert development_score(board, chess.WHITE) >= 4
    assert development_score(board, chess.WHITE) > development_score(board, chess.BLACK)


@pytest.mark.parametrize(
    "fen,expected",
    [
        ("4k3/8/8/8/8/8/8/4K3 w - - 0 1", "open"),
        # Par único travado (d5/d6): centro fixo, não fechado.
        ("4k3/8/3p4/3P4/8/8/8/4K3 w - - 0 1", "fixed"),
        # Italiana: e4/e5 travados isoladamente => centro fixo.
        ("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 3", "fixed"),
        # Francesa do avanço: d4/d5 e e5/e6 travados => centro fechado.
        ("rnbqkbnr/pp3ppp/4p3/2ppP3/3P4/8/PPP2PPP/RNBQKBNR w KQkq - 0 4", "closed"),
        ("4k3/8/4p3/3P4/8/8/8/4K3 w - - 0 1", "dynamic"),
        ("4k3/3p4/8/8/4P3/8/8/4K3 w - - 0 1", "fixed"),
        ("4k3/8/8/8/3PP3/8/8/4K3 w - - 0 1", "open"),
    ],
)
def test_center_classification(fen, expected):
    assert classify_center(chess.Board(fen)) == expected


def test_isolated_and_doubled_pawns():
    board = chess.Board("4k3/8/8/8/8/2P5/2P5/4K3 w - - 0 1")
    report = analyze_structure(board, chess.WHITE)
    assert set(report.isolated) == {chess.C2, chess.C3}
    assert set(report.doubled) == {chess.C2, chess.C3}


def test_passed_pawn_detection():
    board = chess.Board("4k3/8/8/3P4/8/8/5p2/4K3 w - - 0 1")
    white = analyze_structure(board, chess.WHITE)
    black = analyze_structure(board, chess.BLACK)
    assert chess.D5 in white.passed
    assert chess.F2 in black.passed


def test_blocked_pawn_is_not_passed():
    board = chess.Board("4k3/8/3p4/3P4/8/8/8/4K3 w - - 0 1")
    report = analyze_structure(board, chess.WHITE)
    assert chess.D5 not in report.passed


def test_backward_pawn_detection():
    # Peão d3 atrás dos vizinhos c4/e4 e com d4 controlado pelo peão preto de e5.
    board = chess.Board("4k3/8/8/4p3/2P1P3/3P4/8/4K3 w - - 0 1")
    report = analyze_structure(board, chess.WHITE)
    assert chess.D3 in report.backward


def test_analyze_position_runs_all_criteria():
    board = chess.Board()
    results = analyze_position(board)
    assert [r.key for r in results] == [
        "material",
        "pawn_majority",
        "development",
        "center",
        "pawn_structure",
    ]
    assert overall_score(results) == pytest.approx(0.0, abs=1e-9)


def test_render_board_produces_svg_with_highlights():
    board = chess.Board("4k3/8/8/3P4/8/8/8/4K3 w - - 0 1")
    results = analyze_position(board)
    svg = render_board(board, results=results)
    assert svg.startswith("<svg")
    assert "</svg>" in svg

import chess
import pytest

from analysis import analyze_position, overall_score, render_board
from analysis.center import classify_center
from analysis.development import development_score, undeveloped_minors
from analysis.material import count_material, material_value
from analysis.outposts import analyze_outposts_for, is_outpost
from analysis.pawn_majority import count_wing_pawns
from analysis.pawn_structure import analyze_structure
from analysis.space import analyze_space, analyze_space_for
from analysis.weak_squares import analyze_weak_squares_for, is_neutralized, is_weak_square


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
        "weak_squares",
        "outposts",
        "space",
    ]
    assert overall_score(results) == pytest.approx(0.0, abs=1e-9)


def test_weak_square_detection():
    # Peão branco em e4 controla d5/f5; d5 não é defendida por peões pretos.
    board = chess.Board("4k3/8/8/8/4P3/8/8/4K3 w - - 0 1")
    assert is_weak_square(board, chess.BLACK, chess.D5)
    # e5 é defendida pelo peão preto de d6? Não há peões pretos: e5 também fraca.
    assert is_weak_square(board, chess.BLACK, chess.E5)
    # A casa continua fraca mesmo ocupada por peça própria: a fraqueza é da casa,
    # não da ocupação. O peão branco de e4 não é defendido por nenhum peão branco.
    assert is_weak_square(board, chess.WHITE, chess.E4)


def test_weak_square_occupied_by_piece_is_still_weak():
    # Cavalo branco em d4 (campo das brancas, sem peão que o defenda).
    board = chess.Board("4k3/8/8/8/3N4/8/8/4K3 w - - 0 1")
    assert is_weak_square(board, chess.WHITE, chess.D4)


def test_weak_square_neutralized_by_defended_piece():
    # Cavalo branco em d4 defendido pelo bispo de e3 e sem peão branco que defenda
    # d4 nem peão preto que o ataque: a casa é fraca, mas a fraqueza está
    # neutralizada na prática pela peça que a ocupa e defende.
    board = chess.Board("4k3/8/8/8/3N4/4B3/8/4K3 w - - 0 1")
    assert is_weak_square(board, chess.WHITE, chess.D4)
    assert is_neutralized(board, chess.WHITE, chess.D4)
    report = analyze_weak_squares_for(board, chess.WHITE)
    assert chess.D4 in report.neutralized
    assert chess.D4 not in report.exploitable


def test_weak_square_exploitable_when_piece_undefended():
    # Cavalo branco em d4 sem defesa: a fraqueza é explorável pelo adversário.
    board = chess.Board("4k3/8/8/8/3N4/8/8/4K3 w - - 0 1")
    assert not is_neutralized(board, chess.WHITE, chess.D4)
    report = analyze_weak_squares_for(board, chess.WHITE)
    assert chess.D4 in report.exploitable


def test_weak_squares_in_example_include_f6_and_h6_without_distant_noise():
    board = chess.Board("r1b1kbqr/pppp1p1p/2n5/4pN2/2B1P3/8/PPPP1PPP/RNBQK2R b KQkq - 4 3")
    report = analyze_weak_squares_for(board, chess.BLACK)
    assert {chess.F6, chess.H6} <= set(report.weak)
    assert chess.H1 not in report.weak
    highlights = analyze_position(board)[5].highlights
    assert chess.F6 in highlights and chess.H6 in highlights


def test_weak_square_covered_by_pawn_is_not_weak():
    # O peão preto de c7 defende b6 e d6: essas casas não são fracas para as pretas.
    board = chess.Board("4k3/2p5/8/8/8/8/8/4K3 w - - 0 1")
    assert not is_weak_square(board, chess.BLACK, chess.B6)
    assert not is_weak_square(board, chess.BLACK, chess.D6)


def test_weak_squares_criterion_scores_control():
    # A ausência do peão preto de g deixa f6 e h6 fracas no campo preto.
    board = chess.Board("r1b1kbqr/pppp1p1p/2n5/4pN2/2B1P3/8/PPPP1PPP/RNBQK2R b KQkq - 4 3")
    result = analyze_position(board)[5]
    assert result.key == "weak_squares"
    assert result.score > 0


def test_outpost_detection():
    # Cavalo branco em d5, defendido pelo peão de c4, sem peão preto que o ataque.
    board = chess.Board("4k3/8/8/3N4/2P5/8/8/4K3 w - - 0 1")
    assert is_outpost(board, chess.WHITE, chess.D5)
    report = analyze_outposts_for(board, chess.WHITE)
    assert chess.D5 in report.outposts
    assert chess.D5 in report.occupied


def test_outpost_expelled_by_pawn_is_not_outpost():
    # Peão preto em e6 ataca d5: o cavalo poderia ser expulso, não é outpost.
    board = chess.Board("4k3/8/4p3/3N4/2P5/8/8/4K3 w - - 0 1")
    assert not is_outpost(board, chess.WHITE, chess.D5)


def test_outpost_requires_pawn_support():
    # Cavalo em d5 sem peão de apoio não configura outpost.
    board = chess.Board("4k3/8/8/3N4/8/8/8/4K3 w - - 0 1")
    assert not is_outpost(board, chess.WHITE, chess.D5)


def test_outpost_without_nearby_minor_is_still_a_candidate():
    board = chess.Board("4k3/8/8/8/2P5/8/8/1N2K1N1 w - - 0 1")
    report = analyze_outposts_for(board, chess.WHITE)
    assert chess.D5 in report.outposts
    assert chess.D5 in report.central
    assert chess.D5 not in report.occupied


def test_outpost_can_be_challenged_by_advancing_enemy_pawn():
    board = chess.Board("4k3/2p5/8/8/2P5/8/8/1N2K1N1 w - - 0 1")
    assert not is_outpost(board, chess.WHITE, chess.D5)


def test_outpost_example_f5_is_occupied_and_central():
    board = chess.Board("r1b1kbqr/pppp1p1p/2n5/4pN2/2B1P3/8/PPPP1PPP/RNBQK2R b KQkq - 4 3")
    report = analyze_outposts_for(board, chess.WHITE)
    assert chess.F5 in report.outposts
    assert chess.F5 in report.occupied
    assert chess.F5 in report.central
    assert not is_outpost(board, chess.WHITE, chess.F6)


def test_outposts_criterion_runs():
    board = chess.Board("4k3/8/8/3N4/2P5/8/8/4K3 w - - 0 1")
    result = analyze_position(board)[6]
    assert result.key == "outposts"
    assert result.score > 0


def test_space_is_balanced_at_start_and_independent_of_turn():
    board = chess.Board()
    result = analyze_space(board)
    assert result.score == 0
    assert not result.highlights
    assert analyze_space_for(board, chess.WHITE).mobility_per_piece == (
        analyze_space_for(board, chess.BLACK).mobility_per_piece
    )
    board.turn = chess.BLACK
    assert analyze_space(board).score == result.score


def test_space_pawn_advance_gains_safe_territory():
    board = chess.Board("4k3/8/8/4P3/8/8/8/4K3 w - - 0 1")
    white = analyze_space_for(board, chess.WHITE)
    assert {chess.E5, chess.D6, chess.F6} <= white.territory
    assert {chess.E5, chess.D6, chess.F6} <= white.pawn_territory
    result = analyze_space(board)
    assert result.score > 0
    assert {chess.E5, chess.D6, chess.F6} <= set(result.highlights)
    assert result.white_plans and result.black_plans


def test_space_score_reverses_when_colors_are_swapped():
    board = chess.Board("4k3/8/8/4P3/8/8/8/4K3 w - - 0 1")
    flipped = board.mirror()
    assert analyze_space(flipped).score == -analyze_space(board).score
    assert {chess.E4, chess.D3, chess.F3} <= analyze_space_for(
        flipped, chess.BLACK
    ).territory


def test_space_excludes_pawn_contested_and_enemy_occupied_squares():
    board = chess.Board("r3k3/2p5/8/4P3/8/8/8/R3K3 w - - 0 1")
    white = analyze_space_for(board, chess.WHITE)
    assert chess.D6 not in white.territory  # c7 attacks d6
    assert chess.A8 not in white.territory  # enemy rook occupies a8
    assert chess.A6 in white.territory  # rook controls empty enemy territory


def test_space_mobility_decreases_when_enemy_pawn_restricts_piece():
    board = chess.Board("4k3/8/6p1/8/3N4/8/8/4K3 w - - 0 1")
    with_pawn = analyze_space_for(board, chess.WHITE)
    board.remove_piece_at(chess.G6)
    without_pawn = analyze_space_for(board, chess.WHITE)
    assert with_pawn.mobility == without_pawn.mobility - 1
    assert with_pawn.piece_count == without_pawn.piece_count == 1


def test_space_mobility_excludes_friendly_occupied_targets():
    board = chess.Board("4k3/8/8/8/3N4/8/2P5/4K3 w - - 0 1")
    assert analyze_space_for(board, chess.WHITE).mobility == 7


def test_render_board_produces_svg_with_highlights():
    board = chess.Board("4k3/8/8/3P4/8/8/8/4K3 w - - 0 1")
    results = analyze_position(board)
    svg = render_board(board, results=results)
    assert svg.startswith("<svg")
    assert "</svg>" in svg

"""Critério 3 — Desenvolvimento e tempo."""

from __future__ import annotations

import chess

from analysis.board_utils import (
    MINOR_HOME_SQUARES,
    QUEEN_HOME_SQUARE,
    has_castled,
    rooks_connected,
    square_list,
)
from analysis.types import BAD, FILL, GOOD, WARN, CriterionResult, Metric, clamp

NATURAL_SQUARES = {
    chess.B1: chess.C3,
    chess.G1: chess.F3,
    chess.C1: chess.F4,
    chess.F1: chess.E2,
    chess.B8: chess.C6,
    chess.G8: chess.F6,
    chess.C8: chess.F5,
    chess.F8: chess.E7,
}


def undeveloped_minors(board: chess.Board, color: chess.Color) -> list[chess.Square]:
    """Cavalos e bispos ainda parados na casa inicial."""
    result = []
    for square in MINOR_HOME_SQUARES[color]:
        piece = board.piece_at(square)
        if piece is not None and piece.color == color and piece.piece_type in (
            chess.KNIGHT,
            chess.BISHOP,
        ):
            result.append(square)
    return result


def developed_minor_count(board: chess.Board, color: chess.Color) -> int:
    minors = list(board.pieces(chess.KNIGHT, color)) + list(board.pieces(chess.BISHOP, color))
    home = set(MINOR_HOME_SQUARES[color])
    return sum(1 for square in minors if square not in home)


def _early_queen(board: chess.Board, color: chess.Color) -> bool:
    """Dama fora de casa enquanto duas ou mais menores ainda não saíram."""
    queens = board.pieces(chess.QUEEN, color)
    if not queens:
        return False
    out = any(square != QUEEN_HOME_SQUARE[color] for square in queens)
    return out and len(undeveloped_minors(board, color)) >= 2


def development_score(board: chess.Board, color: chess.Color) -> int:
    """Pontos de desenvolvimento: menores + roque + torres conectadas."""
    score = developed_minor_count(board, color)
    if has_castled(board, color):
        score += 1
    if rooks_connected(board, color):
        score += 1
    return score


def analyze_development(board: chess.Board) -> CriterionResult:
    findings: list[str] = []
    highlights: dict[chess.Square, str] = {}
    plans: dict[chess.Color, list[str]] = {chess.WHITE: [], chess.BLACK: []}

    stats = {}
    for color in (chess.WHITE, chess.BLACK):
        side = "Brancas" if color == chess.WHITE else "Pretas"
        minors = developed_minor_count(board, color)
        pending = undeveloped_minors(board, color)
        castled = has_castled(board, color)
        connected = rooks_connected(board, color)
        stats[color] = {
            "minors": minors,
            "pending": pending,
            "castled": castled,
            "connected": connected,
            "score": development_score(board, color),
        }

        good_fill = FILL[GOOD] if color == chess.WHITE else FILL[BAD]
        for square in pending:
            highlights[square] = FILL[WARN]

        if pending:
            findings.append(
                f"{side}: peças menores ainda na casa inicial em {square_list(pending)}."
            )
            for square in pending:
                target = NATURAL_SQUARES.get(square)
                if target is not None and board.piece_at(target) is None:
                    plans[color].append(
                        f"Desenvolva {chess.square_name(square)} → "
                        f"{chess.square_name(target)} (casa natural livre)."
                    )
        else:
            findings.append(f"{side}: todas as peças menores desenvolvidas.")

        if castled:
            king_square = board.king(color)
            if king_square is not None:
                highlights.setdefault(king_square, good_fill)
        else:
            findings.append(f"{side}: rei ainda não está abrigado (sem roque).")
            plans[color].append("Role o mais cedo possível para conectar as torres.")

        if connected:
            findings.append(f"{side}: torres conectadas.")
        else:
            plans[color].append("Termine o desenvolvimento e conecte as torres.")

        if _early_queen(board, color):
            findings.append(f"{side}: dama saiu cedo com o desenvolvimento incompleto.")
            plans[color].append("Evite perder tempo com a dama exposta; traga as peças menores.")

    white_score = stats[chess.WHITE]["score"]
    black_score = stats[chess.BLACK]["score"]
    diff = white_score - black_score

    if diff == 0:
        verdict = "Desenvolvimento equivalente para os dois lados."
    else:
        side = "Brancas" if diff > 0 else "Pretas"
        verdict = f"{side} estão à frente em desenvolvimento ({abs(diff)} tempo(s))."
        leader = chess.WHITE if diff > 0 else chess.BLACK
        follower = not leader
        if abs(diff) >= 2:
            plans[leader].insert(
                0, "Abra o jogo e ataque rápido: a vantagem de desenvolvimento é temporária."
            )
            plans[follower].insert(
                0, "Mantenha a posição fechada e troque peças até completar o desenvolvimento."
            )

    metrics = [
        Metric(
            "Menores desenvolvidas",
            f"{stats[chess.WHITE]['minors']} x {stats[chess.BLACK]['minors']}",
        ),
        Metric(
            "Roque feito",
            f"{'sim' if stats[chess.WHITE]['castled'] else 'não'} x "
            f"{'sim' if stats[chess.BLACK]['castled'] else 'não'}",
        ),
        Metric("Índice de tempo (B-P)", f"{diff:+d}", delta=f"{diff:+d}"),
    ]

    return CriterionResult(
        key="development",
        title="Desenvolvimento / tempo",
        icon=":material/rocket_launch:",
        verdict=verdict,
        score=clamp(diff / 4.0),
        metrics=metrics,
        findings=findings,
        white_plans=plans[chess.WHITE] or ["Desenvolvimento pronto: escolha um plano de ataque."],
        black_plans=plans[chess.BLACK] or ["Desenvolvimento pronto: escolha um plano de ataque."],
        highlights=highlights,
    )

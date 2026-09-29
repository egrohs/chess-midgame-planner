"""Critério 2 — Maioria de peões por ala."""

from __future__ import annotations

import chess

from analysis.board_utils import (
    WING_FILES,
    WING_LABELS,
    advance_square,
    most_advanced,
    pawn_files,
    pawns,
)
from analysis.types import BAD, FILL, GOOD, Arrow, CriterionResult, Metric, clamp


def count_wing_pawns(board: chess.Board, color: chess.Color) -> dict[str, int]:
    files = pawn_files(board, color)
    return {wing: sum(1 for f in files if f in indexes) for wing, indexes in WING_FILES.items()}


def _wing_pawns(board: chess.Board, color: chess.Color, wing: str) -> list[chess.Square]:
    indexes = WING_FILES[wing]
    return [sq for sq in pawns(board, color) if chess.square_file(sq) in indexes]


def analyze_pawn_majority(board: chess.Board) -> CriterionResult:
    white = count_wing_pawns(board, chess.WHITE)
    black = count_wing_pawns(board, chess.BLACK)

    findings: list[str] = []
    highlights: dict[chess.Square, str] = {}
    arrows: list[Arrow] = []
    white_plans: list[str] = []
    black_plans: list[str] = []
    score = 0.0

    for wing in ("queenside", "center", "kingside"):
        delta = white[wing] - black[wing]
        label = WING_LABELS[wing]
        if delta == 0:
            findings.append(f"Peões equilibrados na {label}: {white[wing]}x{black[wing]}.")
            continue

        leader = chess.WHITE if delta > 0 else chess.BLACK
        side = "Brancas" if leader == chess.WHITE else "Pretas"
        findings.append(
            f"{side} com maioria na {label}: {white[wing]}x{black[wing]} ({abs(delta):+d})."
        )

        fill = FILL[GOOD] if leader == chess.WHITE else FILL[BAD]
        squares = _wing_pawns(board, leader, wing)
        for square in squares:
            highlights[square] = fill

        spearhead = most_advanced(squares, leader)
        if spearhead is not None:
            arrows.append(Arrow(spearhead, advance_square(spearhead, leader, 2), fill))

        if wing == "center":
            plan = "Use a maioria central para ganhar espaço e abrir linhas para as peças."
        else:
            plan = (
                f"Avance a maioria na {label} para criar um peão passado; "
                "apoie o avanço com o rei no final."
            )
        counter = f"Segure a maioria adversária na {label} e contra-ataque na ala oposta."
        if leader == chess.WHITE:
            white_plans.append(plan)
            black_plans.append(counter)
            score += 0.22 * delta
        else:
            black_plans.append(plan)
            white_plans.append(counter)
            score += 0.22 * delta

    total_white, total_black = sum(white.values()), sum(black.values())
    if total_white != total_black:
        findings.append(
            f"Total de peões: brancas {total_white} x pretas {total_black}."
        )

    balanced = all(white[w] == black[w] for w in WING_FILES)
    verdict = (
        "Nenhuma maioria de peões: estrutura simétrica por alas."
        if balanced
        else "Existem maiorias de peões que definem em qual ala jogar."
    )

    metrics = [
        Metric("Ala da dama (a-c)", f"{white['queenside']} x {black['queenside']}"),
        Metric("Centro (d-e)", f"{white['center']} x {black['center']}"),
        Metric("Ala do rei (f-h)", f"{white['kingside']} x {black['kingside']}"),
    ]

    return CriterionResult(
        key="pawn_majority",
        title="Maioria de peões",
        icon=":material/bar_chart:",
        verdict=verdict,
        score=clamp(score),
        metrics=metrics,
        findings=findings,
        white_plans=white_plans or ["Jogue na ala onde tiver mais espaço."],
        black_plans=black_plans or ["Jogue na ala onde tiver mais espaço."],
        highlights=highlights,
        arrows=arrows,
    )

"""Critério 1 — Material bruto."""

from __future__ import annotations

import chess

from analysis.types import BAD, FILL, GOOD, CriterionResult, Metric, clamp

PIECE_VALUES: dict[chess.PieceType, float] = {
    chess.PAWN: 1.0,
    chess.KNIGHT: 3.0,
    chess.BISHOP: 3.25,
    chess.ROOK: 5.0,
    chess.QUEEN: 9.0,
}

PIECE_NAMES = {
    chess.PAWN: "peões",
    chess.KNIGHT: "cavalos",
    chess.BISHOP: "bispos",
    chess.ROOK: "torres",
    chess.QUEEN: "damas",
}


def count_material(board: chess.Board, color: chess.Color) -> dict[chess.PieceType, int]:
    return {ptype: len(board.pieces(ptype, color)) for ptype in PIECE_VALUES}


def material_value(counts: dict[chess.PieceType, int]) -> float:
    return sum(PIECE_VALUES[ptype] * n for ptype, n in counts.items())


def analyze_material(board: chess.Board) -> CriterionResult:
    white = count_material(board, chess.WHITE)
    black = count_material(board, chess.BLACK)
    white_value = material_value(white)
    black_value = material_value(black)
    diff = white_value - black_value

    findings: list[str] = []
    highlights: dict[chess.Square, str] = {}

    for ptype in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN):
        delta = white[ptype] - black[ptype]
        if delta == 0:
            continue
        leader = chess.WHITE if delta > 0 else chess.BLACK
        side = "Brancas" if leader else "Pretas"
        findings.append(f"{side} com {abs(delta)} {PIECE_NAMES[ptype]} a mais.")
        fill = FILL[GOOD] if leader == chess.WHITE else FILL[BAD]
        for square in board.pieces(ptype, leader):
            highlights[square] = fill

    white_pair = white[chess.BISHOP] >= 2
    black_pair = black[chess.BISHOP] >= 2
    if white_pair and not black_pair:
        findings.append("Brancas têm o par de bispos.")
    elif black_pair and not white_pair:
        findings.append("Pretas têm o par de bispos.")

    if abs(diff) < 0.25:
        verdict = "Material equilibrado."
    elif abs(diff) < 1.5:
        side = "Brancas" if diff > 0 else "Pretas"
        verdict = f"Pequena vantagem material para as {side.lower()} ({abs(diff):+.2f})."
    elif abs(diff) < 3.0:
        side = "Brancas" if diff > 0 else "Pretas"
        verdict = f"{side} ganham um peão ou mais de material ({abs(diff):.2f})."
    else:
        side = "Brancas" if diff > 0 else "Pretas"
        verdict = f"Vantagem material decisiva das {side.lower()} ({abs(diff):.2f})."

    white_plans: list[str] = []
    black_plans: list[str] = []
    if diff >= 1.0:
        white_plans.append("Simplifique: troque peças (não peões) para converter o material extra.")
        black_plans.append("Evite trocas; busque compensação dinâmica e complique a posição.")
    elif diff <= -1.0:
        black_plans.append("Simplifique: troque peças (não peões) para converter o material extra.")
        white_plans.append("Evite trocas; busque compensação dinâmica e complique a posição.")
    else:
        white_plans.append("Sem desequilíbrio material: decida pelo critério posicional.")
        black_plans.append("Sem desequilíbrio material: decida pelo critério posicional.")

    if white_pair and not black_pair:
        white_plans.append("Abra a posição para valorizar o par de bispos.")
    if black_pair and not white_pair:
        black_plans.append("Abra a posição para valorizar o par de bispos.")

    metrics = [
        Metric("Material brancas", f"{white_value:.2f}"),
        Metric("Material pretas", f"{black_value:.2f}"),
        Metric("Saldo (brancas)", f"{diff:+.2f}", delta=f"{diff:+.2f}"),
    ]

    return CriterionResult(
        key="material",
        title="Material bruto",
        icon=":material/scale:",
        verdict=verdict,
        score=clamp(diff / 5.0),
        metrics=metrics,
        findings=findings or ["Nenhum desequilíbrio de peças."],
        white_plans=white_plans,
        black_plans=black_plans,
        highlights=highlights,
    )

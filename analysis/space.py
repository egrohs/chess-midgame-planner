"""Critério 8 — Espaço: território sustentado e mobilidade das peças.

Território são casas da metade adversária ocupadas ou controladas por peões
e peças (exceto o rei), sem peão adversário que as ataque. Casas ocupadas por
peças adversárias não contam como território seguro. Mobilidade é a média de
destinos geométricos disponíveis por peça não peão, excluindo casas próprias
e as atacadas por peões adversários; não substitui a análise de lances legais.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import chess

from analysis.board_utils import pawn_controlled_squares, relative_rank, square_list
from analysis.types import BAD, FILL, GOOD, CriterionResult, Metric, clamp

MOBILE_PIECES = (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)


@dataclass
class SpaceReport:
    territory: set[chess.Square] = field(default_factory=set)
    pawn_territory: set[chess.Square] = field(default_factory=set)
    mobility: int = 0
    piece_count: int = 0

    @property
    def mobility_per_piece(self) -> float:
        return self.mobility / self.piece_count if self.piece_count else 0.0


def analyze_space_for(board: chess.Board, color: chess.Color) -> SpaceReport:
    """Mede domínio estável no campo oposto e opções de movimento sem peões rivais."""
    report = SpaceReport()
    hostile_pawns = pawn_controlled_squares(board, not color)
    own_pawns = board.pieces(chess.PAWN, color)
    pawn_control = pawn_controlled_squares(board, color)
    controlled = set(pawn_control)
    controlled.update(own_pawns)

    for piece_type in MOBILE_PIECES:
        for source in board.pieces(piece_type, color):
            attacks = set(board.attacks(source))
            controlled.update(attacks)
            report.piece_count += 1
            report.mobility += sum(
                board.color_at(target) != color and target not in hostile_pawns
                for target in attacks
            )

    for square in controlled:
        if relative_rank(square, color) < 4 or square in hostile_pawns:
            continue
        if board.color_at(square) == (not color):
            continue
        report.territory.add(square)
        if square in own_pawns or square in pawn_control:
            report.pawn_territory.add(square)
    return report


def analyze_space(board: chess.Board) -> CriterionResult:
    white = analyze_space_for(board, chess.WHITE)
    black = analyze_space_for(board, chess.BLACK)
    diff = (
        (len(white.territory) - len(black.territory)) / 12
        + (white.mobility_per_piece - black.mobility_per_piece) / 8
    )
    score = clamp(diff / 2)

    if abs(score) <= 0.05:
        verdict = "Espaço e liberdade das peças equilibrados."
    elif score > 0:
        verdict = "Brancas têm mais espaço e liberdade para manobrar."
    else:
        verdict = "Pretas têm mais espaço e liberdade para manobrar."

    highlights = {square: FILL[GOOD] for square in white.territory}
    highlights.update({square: FILL[BAD] for square in black.territory})
    findings = [
        f"Casas no campo adversário sem ataque de peões rivais: brancas {len(white.territory)} x "
        f"pretas {len(black.territory)} casas.",
        f"Controle por peões (incluindo suas casas): brancas {len(white.pawn_territory)} x "
        f"pretas {len(black.pawn_territory)} casas.",
        f"Mobilidade média por peça (sem casas próprias nem atacadas por peões): "
        f"brancas {white.mobility_per_piece:.1f} x pretas {black.mobility_per_piece:.1f}.",
    ]
    if white.territory:
        findings.append(f"Casas dominadas pelas brancas: {square_list(white.territory)}.")
    if black.territory:
        findings.append(f"Casas dominadas pelas pretas: {square_list(black.territory)}.")

    def plans(mine: SpaceReport, theirs: SpaceReport) -> list[str]:
        actions = []
        if len(mine.territory) < len(theirs.territory):
            actions.append(
                "Ganhe terreno com avanços de peões bem apoiados e conteste as casas "
                "controladas pelo adversário antes de instalar peças nelas."
            )
        elif mine.territory:
            actions.append(
                "Aproveite o espaço para manobrar as peças atrás dos peões e "
                "pressionar as casas no campo adversário."
            )
        if mine.piece_count and mine.mobility_per_piece < theirs.mobility_per_piece:
            actions.append(
                "Suas peças têm menos liberdade: abra uma linha ou reorganize a "
                "peça mais restrita antes de iniciar novas operações."
            )
        if not actions:
            actions.append(
                "Desenvolva as peças e avance peões com apoio para conquistar "
                "casas no campo adversário sem pressão de peões rivais."
            )
        return actions

    return CriterionResult(
        key="space",
        title="Espaço",
        icon=":material/open_with:",
        verdict=verdict,
        score=score,
        metrics=[
            Metric("Casas no campo rival (B x P)", f"{len(white.territory)} x {len(black.territory)}"),
            Metric("Casas por peões (B x P)", f"{len(white.pawn_territory)} x {len(black.pawn_territory)}"),
            Metric("Mobilidade por peça (B x P)", f"{white.mobility_per_piece:.1f} x {black.mobility_per_piece:.1f}"),
        ],
        findings=findings,
        white_plans=plans(white, black),
        black_plans=plans(black, white),
        highlights=highlights,
    )

"""Critério 9 — Atividade das peças: mobilidade ponderada pela qualidade das casas.

Avalia cavalos, bispos, torres e damas. Uma casa acessível vale mais no centro,
no campo adversário ou quando apoiada por peão; ataques de peões adversários
descartam a casa e a contestação por outras peças reduz seu valor. Trata-se
de uma heurística posicional, não de um cálculo de lances legais ou trocas.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import chess

from analysis.board_utils import pawn_controlled_squares, relative_rank, square_list
from analysis.space import MOBILE_PIECES
from analysis.types import BAD, FILL, GOOD, WARN, CriterionResult, Metric, clamp


@dataclass(frozen=True)
class PieceActivity:
    square: chess.Square
    piece_type: chess.PieceType
    destinations: int
    quality: float


@dataclass
class ActivityReport:
    pieces: list[PieceActivity] = field(default_factory=list)

    @property
    def average(self) -> float:
        return sum(piece.quality for piece in self.pieces) / len(self.pieces) if self.pieces else 0.0

    @property
    def restricted(self) -> list[chess.Square]:
        return [piece.square for piece in self.pieces if piece.quality < 2.0]

    @property
    def best(self) -> PieceActivity | None:
        return max(self.pieces, key=lambda piece: piece.quality, default=None)

    @property
    def worst(self) -> PieceActivity | None:
        return min(self.pieces, key=lambda piece: piece.quality, default=None)


def _central(square: chess.Square) -> bool:
    return 2 <= chess.square_file(square) <= 5 and 2 <= chess.square_rank(square) <= 5


def analyze_activity_for(board: chess.Board, color: chess.Color) -> ActivityReport:
    """Mede oportunidades posicionais por peça, independentemente de quem joga."""
    friendly_pawns = pawn_controlled_squares(board, color)
    hostile_pawns = pawn_controlled_squares(board, not color)
    report = ActivityReport()

    for piece_type in MOBILE_PIECES:
        for source in sorted(board.pieces(piece_type, color)):
            quality = 0.0
            destinations = 0
            for target in board.attacks(source):
                if board.piece_at(target) is not None or target in hostile_pawns:
                    continue
                destinations += 1
                value = 1.0
                if _central(target):
                    value += 0.5
                if relative_rank(target, color) >= 4:
                    value += 0.25
                if target in friendly_pawns:
                    value += 0.25
                if board.is_attacked_by(not color, target):
                    value *= 0.65 if target in friendly_pawns else 0.35
                quality += value

            if source in hostile_pawns:
                quality = max(0.0, quality - 1.0)
            elif relative_rank(source, color) >= 4 and source in friendly_pawns:
                quality += 0.5
            report.pieces.append(PieceActivity(source, piece_type, destinations, quality))
    return report


def analyze_piece_activity(board: chess.Board) -> CriterionResult:
    white = analyze_activity_for(board, chess.WHITE)
    black = analyze_activity_for(board, chess.BLACK)
    score = (
        clamp((white.average - black.average) / 6.0)
        if white.pieces and black.pieces
        else 0.0
    )

    if abs(score) <= 0.05:
        verdict = "Atividade das peças aproximadamente equilibrada."
    elif score > 0:
        verdict = "Peças brancas têm melhores casas para atuar."
    else:
        verdict = "Peças pretas têm melhores casas para atuar."

    highlights: dict[chess.Square, str] = {}
    for report, good in ((white, GOOD), (black, BAD)):
        if report.best is not None:
            highlights[report.best.square] = FILL[good]
        for square in report.restricted:
            highlights[square] = FILL[WARN]

    def describe(report: ActivityReport, side: str) -> list[str]:
        if not report.pieces:
            return [f"{side}: nenhuma peça menor ou pesada para avaliar."]
        lines = [
            f"{side}: {len(report.pieces)} peças, atividade média {report.average:.1f}; "
            f"{len(report.restricted)} com poucas opções úteis."
        ]
        if report.best:
            lines.append(
                f"{side}: peça mais ativa em {chess.square_name(report.best.square)} "
                f"(índice {report.best.quality:.1f}; {report.best.destinations} casas consideradas)."
            )
        if report.restricted:
            lines.append(f"{side}: peças restritas em {square_list(report.restricted)}.")
        return lines

    def plans(report: ActivityReport) -> list[str]:
        if not report.pieces:
            return ["Sem peças menores ou pesadas para manobrar; coordene rei e peões."]
        if report.worst is not None and report.worst.quality < 2.0:
            return [
                f"Melhore a peça em {chess.square_name(report.worst.square)}: "
                "abra uma linha ou busque casas centrais protegidas por peões, "
                "sem entrar em casas atacadas por peões rivais."
            ]
        return [
            "Mantenha as peças ativas; prefira casas centrais sustentadas e "
            "evite avanços que reduzam sua liberdade."
        ]

    return CriterionResult(
        key="piece_activity",
        title="Atividade das peças",
        icon=":material/move_up:",
        verdict=verdict,
        score=score,
        metrics=[
            Metric("Índice médio (B x P)", f"{white.average:.1f} x {black.average:.1f}"),
            Metric("Peças restritas (B x P)", f"{len(white.restricted)} x {len(black.restricted)}"),
            Metric("Peças avaliadas (B x P)", f"{len(white.pieces)} x {len(black.pieces)}"),
        ],
        findings=describe(white, "Brancas") + describe(black, "Pretas") + [
            "Índice heurístico: casas livres centrais, avançadas e apoiadas valem mais; "
            "casas atacadas por peões não contam. Não são lances legais nem táticas."
        ],
        white_plans=plans(white),
        black_plans=plans(black),
        highlights=highlights,
    )

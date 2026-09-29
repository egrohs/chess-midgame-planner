"""Critério 7 — Outposts (casa fraca + apoio de peão + expulsão).

Um *outpost* é uma casa na metade adversária que:

1. é uma casa fraca para o adversário (ele não a defende com peões);
2. é defendida por um peão nosso;
3. não pode ser atacada/expulsada por peões inimigos.

A casa é um posto potencial mesmo sem peça menor próxima. Quanto mais avançada
e central, mais valioso; distingue-se o posto já ocupado por peça menor.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import chess

from analysis.board_utils import pawn_attacks_square, relative_rank, square_list
from analysis.types import BAD, FILL, GOOD, INFO, WARN, Arrow, CriterionResult, Metric, clamp
from analysis.weak_squares import is_weak_square

#: Fileira relativa mínima para a casa estar na metade adversária.
ENEMY_HALF_RANK = 4
#: Fileira relativa a partir da qual o outpost é considerado avançado.
ADVANCED_RANK = 5


@dataclass
class OutpostReport:
    #: casas que atendem a todos os critérios de outpost
    outposts: list[chess.Square] = field(default_factory=list)
    #: subconjunto de ``outposts`` no centro ampliado (c-f)
    central: list[chess.Square] = field(default_factory=list)
    #: subconjunto de ``outposts`` já avançado (fileira relativa >= 5)
    advanced: list[chess.Square] = field(default_factory=list)
    #: outposts já ocupados por uma peça menor nossa
    occupied: list[chess.Square] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.outposts)


def _supported_by_pawn(board: chess.Board, color: chess.Color, square: chess.Square) -> bool:
    """A casa é defendida por um peão da cor."""
    return pawn_attacks_square(board, color, square)


def _can_be_expelled_by_pawn(
    board: chess.Board, color: chess.Color, square: chess.Square
) -> bool:
    """Algum peão inimigo ataca a casa (poderia expulsar a peça)?"""
    return pawn_attacks_square(board, not color, square)


def is_outpost(board: chess.Board, color: chess.Color, square: chess.Square) -> bool:
    """Posto potencial na metade adversária, apoiado e não expulsável por peões."""
    if relative_rank(square, color) < ENEMY_HALF_RANK:
        return False
    if not is_weak_square(board, not color, square):
        return False
    if not _supported_by_pawn(board, color, square):
        return False
    if _can_be_expelled_by_pawn(board, color, square):
        return False
    return True


def analyze_outposts_for(board: chess.Board, color: chess.Color) -> OutpostReport:
    report = OutpostReport()
    for square in chess.SQUARES:
        if not is_outpost(board, color, square):
            continue
        report.outposts.append(square)
        if 2 <= chess.square_file(square) <= 5:
            report.central.append(square)
        if relative_rank(square, color) >= ADVANCED_RANK:
            report.advanced.append(square)
        piece = board.piece_at(square)
        if (
            piece is not None
            and piece.color == color
            and piece.piece_type in (chess.KNIGHT, chess.BISHOP)
        ):
            report.occupied.append(square)
    return report


def _weight(report: OutpostReport) -> float:
    """Peso do outpost: casas centrais e avançadas valem mais."""
    return len(report.outposts) + len(report.central) + len(report.advanced)


def _describe(report: OutpostReport, side: str) -> list[str]:
    lines = []
    if report.outposts:
        lines.append(f"{side}: outposts potenciais em {square_list(report.outposts)}.")
    if report.central:
        lines.append(f"{side}: outposts centrais em {square_list(report.central)}.")
    if report.occupied:
        lines.append(f"{side}: outposts já ocupados por peça menor em {square_list(report.occupied)}.")
    if not lines:
        lines.append(f"{side}: nenhum outpost potencial no momento.")
    return lines


def analyze_outposts(board: chess.Board) -> CriterionResult:
    white = analyze_outposts_for(board, chess.WHITE)
    black = analyze_outposts_for(board, chess.BLACK)

    highlights: dict[chess.Square, str] = {}
    arrows: list[Arrow] = []

    # Outposts das brancas são bons para as brancas (verde) e vice-versa.
    for square in white.outposts:
        highlights[square] = FILL[GOOD]
    for square in black.outposts:
        highlights[square] = FILL[BAD]
    for square in white.central:
        highlights[square] = FILL[WARN]
    for square in black.central:
        highlights[square] = FILL[WARN]

    # Seta apontando a peça menor mais próxima para o outpost central.
    for report, color in ((white, chess.WHITE), (black, chess.BLACK)):
        for square in report.central:
            if square in report.occupied:
                continue
            source = _nearest_minor(board, color, square)
            if source is not None:
                arrows.append(Arrow(source, square, FILL[INFO]))

    findings = _describe(white, "Brancas") + _describe(black, "Pretas")

    white_plans: list[str] = []
    black_plans: list[str] = []

    def add_plans(report: OutpostReport, mine: list[str], theirs: list[str]) -> None:
        if report.outposts:
            mine.append(
                f"Planeje ocupar o(s) outpost(s) em {square_list(report.outposts)} com um cavalo: "
                "são postos potenciais, não necessariamente acessíveis agora."
            )
            theirs.append(
                f"Impeça a ocupação dos outposts adversários em {square_list(report.outposts)}: "
                "troque a peça que os defende ou dispute a casa com uma peça sua."
            )
        if report.central:
            mine.append(
                f"Priorize os outposts centrais em {square_list(report.central)} — "
                "de lá a peça domina o tabuleiro."
            )
        if report.occupied:
            mine.append(
                f"Mantenha a peça firme em {square_list(report.occupied)} e apoie-a com peões; "
                "troque apenas por uma peça de valor maior."
            )
        if not report.outposts:
            mine.append("Sem outposts: crie casas fracas no campo adversário avançando peões.")

    add_plans(white, white_plans, black_plans)
    add_plans(black, black_plans, white_plans)

    white_weight = _weight(white)
    black_weight = _weight(black)
    diff = white_weight - black_weight

    if diff == 0:
        verdict = "Nenhum lado tem outposts relevantes."
    elif diff > 0:
        verdict = "Brancas têm os melhores outposts."
    else:
        verdict = "Pretas têm os melhores outposts."

    metrics = [
        Metric("Outposts (B x P)", f"{white.count} x {black.count}"),
        Metric("Outposts centrais (B x P)", f"{len(white.central)} x {len(black.central)}"),
        Metric("Outposts ocupados (B x P)", f"{len(white.occupied)} x {len(black.occupied)}"),
    ]

    return CriterionResult(
        key="outposts",
        title="Outposts",
        icon=":material/where_to_vote:",
        verdict=verdict,
        score=clamp(diff / 4.0),
        metrics=metrics,
        findings=findings,
        white_plans=white_plans,
        black_plans=black_plans,
        highlights=highlights,
        arrows=arrows,
    )


def _nearest_minor(
    board: chess.Board, color: chess.Color, target: chess.Square
) -> chess.Square | None:
    """Peça menor da cor que ataca a casa alvo, a mais próxima dela."""
    candidates = [
        minor
        for minor in list(board.pieces(chess.KNIGHT, color)) + list(board.pieces(chess.BISHOP, color))
        if target in board.attacks(minor)
    ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda sq: chess.square_distance(sq, target),
    )

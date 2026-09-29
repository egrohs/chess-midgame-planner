"""Critério 6 — Casas fracas (controle por peões + estabilidade da casa).

Uma casa é *fraca* para um lado quando esse lado não pode mais defendê-la com
peões: nenhum peão próprio ataca a casa nem pode vir a atacá-la. A fraqueza é
uma propriedade da **casa**, não da ocupação — uma casa continua fraca mesmo que
esteja ocupada por uma peça sua.

A ocupação, porém, muda a *importância prática* da fraqueza:

* se a peça própria ocupa a casa, defende-a e não pode ser expulsa por peões
  inimigos, a fraqueza fica **neutralizada** (o adversário não consegue explorá-la
  enquanto a peça permanecer ali);
* caso contrário, a casa fraca é um **alvo explorável** pelo adversário.

Quanto mais avançada e mais central a casa, mais grave é a fraqueza.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import chess

from analysis.board_utils import (
    CENTER_FILES,
    advance_square,
    pawn_attacks_square,
    pawns,
    relative_rank,
    square_list,
)
from analysis.types import BAD, FILL, GOOD, INFO, WARN, Arrow, CriterionResult, Metric, clamp

#: Fileiras relativas (0 = casa inicial) a partir das quais a fraqueza pesa mais.
ADVANCED_RANK = 3
#: Fileira relativa mínima para a casa ser considerada relevante. Casas muito
#: recuadas (fileira inicial) raramente são exploráveis e só geram ruído.
MIN_RANK = 2


@dataclass
class WeakSquareReport:
    #: casas que o lado não consegue mais defender com peões (ocupadas ou não)
    weak: list[chess.Square] = field(default_factory=list)
    #: subconjunto de ``weak`` que está no centro ampliado (c-f)
    central: list[chess.Square] = field(default_factory=list)
    #: subconjunto de ``weak`` que já está avançado (fileira relativa >= 3)
    advanced: list[chess.Square] = field(default_factory=list)
    #: subconjunto de ``weak`` ocupado por peça própria que a defende e não pode
    #: ser expulsa — a fraqueza existe, mas está neutralizada na prática
    neutralized: list[chess.Square] = field(default_factory=list)
    #: subconjunto de ``weak`` que o adversário pode explorar de fato
    exploitable: list[chess.Square] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.weak)


def _can_be_defended_by_pawn(
    board: chess.Board, color: chess.Color, square: chess.Square
) -> bool:
    """A casa pode ser defendida por um peão atual ou por um peão que ainda venha.

    Um peão só defende casas nas colunas adjacentes e à sua frente. Um peão que
    ainda não passou da casa pode vir a defendê-la ao avançar.
    """
    if pawn_attacks_square(board, color, square):
        return True
    file_index = chess.square_file(square)
    target_rank = relative_rank(square, color)
    for pawn in pawns(board, color):
        if abs(chess.square_file(pawn) - file_index) != 1:
            continue
        if relative_rank(pawn, color) < target_rank:
            return True
    return False


def is_weak_square(board: chess.Board, color: chess.Color, square: chess.Square) -> bool:
    """Casa que a cor não defende com peões.

    A ocupação por peça própria **não** elimina a fraqueza: a casa continua fraca
    mesmo estando ocupada. Use :func:`is_neutralized` para saber se a fraqueza
    tem importância prática.
    """
    if relative_rank(square, color) < MIN_RANK:
        return False
    return not _can_be_defended_by_pawn(board, color, square)


def is_neutralized(board: chess.Board, color: chess.Color, square: chess.Square) -> bool:
    """A fraqueza da casa está neutralizada por uma peça própria que a ocupa.

    Isso acontece quando a casa é fraca, está ocupada por uma peça da cor, essa
    peça **defende** a casa (é defendida por outra peça nossa) e **não pode ser
    expulsa** por peões inimigos. Nesse caso o adversário não consegue explorar a
    fraqueza enquanto a peça permanecer ali.
    """
    if not is_weak_square(board, color, square):
        return False
    piece = board.piece_at(square)
    if piece is None or piece.color != color:
        return False
    # A peça que ocupa precisa estar defendida por outra peça nossa...
    if not board.attackers(color, square):
        return False
    # ...e não pode ser expulsa por um peão inimigo.
    if pawn_attacks_square(board, not color, square):
        return False
    return True


def analyze_weak_squares_for(board: chess.Board, color: chess.Color) -> WeakSquareReport:
    report = WeakSquareReport()
    for square in chess.SQUARES:
        if not is_weak_square(board, color, square):
            continue
        report.weak.append(square)
        if chess.square_file(square) in CENTER_FILES:
            report.central.append(square)
        if relative_rank(square, color) >= ADVANCED_RANK:
            report.advanced.append(square)
        if is_neutralized(board, color, square):
            report.neutralized.append(square)
        else:
            report.exploitable.append(square)
    return report


def _weight(report: WeakSquareReport) -> float:
    """Peso da fraqueza: casas centrais e avançadas contam mais.

    Casas neutralizadas por uma peça própria que as defende pesam apenas metade,
    pois o adversário não consegue explorá-las na prática.
    """
    weight = 0.0
    for square in report.weak:
        value = 1.0
        if square in report.central:
            value += 1.0
        if square in report.advanced:
            value += 1.0
        if square in report.neutralized:
            value *= 0.5
        weight += value
    return weight


def _describe(report: WeakSquareReport, side: str) -> list[str]:
    lines = []
    if report.weak:
        lines.append(
            f"{side}: casas fracas (sem controle de peão) em {square_list(report.weak)}."
        )
    if report.central:
        lines.append(f"{side}: buracos centrais em {square_list(report.central)}.")
    if report.advanced:
        lines.append(f"{side}: casas avançadas indefesas em {square_list(report.advanced)}.")
    if report.neutralized:
        lines.append(
            f"{side}: fraqueza neutralizada por peça própria em "
            f"{square_list(report.neutralized)} — a peça defende a casa e não pode ser expulsa."
        )
    if report.exploitable:
        lines.append(
            f"{side}: casas fracas exploráveis pelo adversário em "
            f"{square_list(report.exploitable)}."
        )
    if not lines:
        lines.append(f"{side}: nenhuma casa fraca relevante — estrutura de peões coesa.")
    return lines


def analyze_weak_squares(board: chess.Board) -> CriterionResult:
    white = analyze_weak_squares_for(board, chess.WHITE)
    black = analyze_weak_squares_for(board, chess.BLACK)

    highlights: dict[chess.Square, str] = {}
    arrows: list[Arrow] = []

    # Casas fracas das brancas são alvos para as pretas (vermelho) e vice-versa.
    for square in white.weak:
        highlights[square] = FILL[BAD]
    for square in black.weak:
        highlights[square] = FILL[GOOD]
    for square in white.central:
        highlights[square] = FILL[WARN]
    for square in black.central:
        highlights[square] = FILL[WARN]
    # Fraquezas neutralizadas ficam em tom informativo (existem, mas não exploráveis).
    for square in white.neutralized:
        highlights[square] = FILL[INFO]
    for square in black.neutralized:
        highlights[square] = FILL[INFO]

    # Sinaliza as casas fracas mais perigosas com uma seta de ocupação.
    for report, color in ((white, chess.WHITE), (black, chess.BLACK)):
        for square in report.exploitable:
            if chess.square_file(square) in CENTER_FILES:
                arrows.append(Arrow(square, advance_square(square, color, 1), FILL[INFO]))

    findings = _describe(white, "Brancas") + _describe(black, "Pretas")

    white_plans: list[str] = []
    black_plans: list[str] = []

    def add_plans(report: WeakSquareReport, mine: list[str], theirs: list[str]) -> None:
        if report.exploitable:
            mine.append(
                f"Suas casas fracas exploráveis em {square_list(report.exploitable)} pedem peças "
                "que as cubram: traga um cavalo ou bispo para defender e evite trocá-lo."
            )
            theirs.append(
                f"Explore as casas fracas adversárias em {square_list(report.exploitable)}: "
                "manobre um cavalo para lá e evite que o adversário as defenda com peões."
            )
        if report.neutralized:
            mine.append(
                f"A fraqueza em {square_list(report.neutralized)} está neutralizada pela sua peça: "
                "mantenha-a defendida e não a troque por peça de menor valor."
            )
            theirs.append(
                f"Para explorar {square_list(report.neutralized)}, primeiro troque ou expulse a peça "
                "que ocupa e defende a casa fraca."
            )
        if report.central:
            theirs.append(
                f"Ocupe os buracos centrais em {square_list(report.central)} com uma peça menor "
                "e apoie-a com peões laterais."
            )
        if not report.weak:
            mine.append("Estrutura sem casas fracas: mantenha os peões e não crie buracos.")

    add_plans(white, white_plans, black_plans)
    add_plans(black, black_plans, white_plans)

    white_weight = _weight(white)
    black_weight = _weight(black)
    diff = black_weight - white_weight  # mais casas fracas para as pretas favorece as brancas

    if diff == 0:
        verdict = "Controle de casas equilibrado entre os dois lados."
    elif diff > 0:
        verdict = "Brancas controlam melhor as casas — as pretas têm mais buracos."
    else:
        verdict = "Pretas controlam melhor as casas — as brancas têm mais buracos."

    metrics = [
        Metric("Casas fracas (B x P)", f"{white.count} x {black.count}"),
        Metric("Buracos centrais (B x P)", f"{len(white.central)} x {len(black.central)}"),
        Metric("Casas avançadas (B x P)", f"{len(white.advanced)} x {len(black.advanced)}"),
        Metric(
            "Neutralizadas (B x P)",
            f"{len(white.neutralized)} x {len(black.neutralized)}",
        ),
    ]

    return CriterionResult(
        key="weak_squares",
        title="Casas fracas",
        icon=":material/grid_off:",
        verdict=verdict,
        score=clamp(diff / 6.0),
        metrics=metrics,
        findings=findings,
        white_plans=white_plans,
        black_plans=black_plans,
        highlights=highlights,
        arrows=arrows,
    )

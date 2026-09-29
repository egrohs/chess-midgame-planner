"""Critério 5 — Estrutura básica de peões (isolados, dobrados, atrasados, passados)."""

from __future__ import annotations

from dataclasses import dataclass, field

import chess

from analysis.board_utils import (
    advance_square,
    forward_square,
    pawns,
    pawns_on_file,
    relative_rank,
    square_list,
)
from analysis.types import BAD, FILL, GOOD, WARN, Arrow, CriterionResult, Metric, clamp


@dataclass
class StructureReport:
    isolated: list[chess.Square] = field(default_factory=list)
    doubled: list[chess.Square] = field(default_factory=list)
    backward: list[chess.Square] = field(default_factory=list)
    passed: list[chess.Square] = field(default_factory=list)

    @property
    def weakness_count(self) -> int:
        return len(set(self.isolated) | set(self.doubled) | set(self.backward))


def _adjacent_files(file_index: int) -> list[int]:
    return [f for f in (file_index - 1, file_index + 1) if 0 <= f <= 7]


def is_isolated(board: chess.Board, square: chess.Square, color: chess.Color) -> bool:
    file_index = chess.square_file(square)
    return not any(
        pawns_on_file(board, color, adj) for adj in _adjacent_files(file_index)
    )


def is_doubled(board: chess.Board, square: chess.Square, color: chess.Color) -> bool:
    return len(pawns_on_file(board, color, chess.square_file(square))) > 1


def is_passed(board: chess.Board, square: chess.Square, color: chess.Color) -> bool:
    file_index = chess.square_file(square)
    own_rank = relative_rank(square, color)
    files = [file_index, *_adjacent_files(file_index)]
    for enemy in pawns(board, not color):
        if chess.square_file(enemy) not in files:
            continue
        # O peão inimigo bloqueia se estiver à frente do nosso peão.
        if relative_rank(enemy, color) > own_rank:
            return False
    return True


def is_backward(board: chess.Board, square: chess.Square, color: chess.Color) -> bool:
    """Peão atrás dos vizinhos, sem apoio, com a casa da frente controlada por peão inimigo."""
    if is_isolated(board, square, color):
        return False

    own_rank = relative_rank(square, color)
    neighbours = [
        sq
        for adj in _adjacent_files(chess.square_file(square))
        for sq in pawns_on_file(board, color, adj)
    ]
    if not neighbours:
        return False
    if any(relative_rank(sq, color) <= own_rank for sq in neighbours):
        return False

    ahead = forward_square(square, color)
    if ahead is None or board.piece_at(ahead) is not None:
        return False

    enemy_pawns = board.pieces(chess.PAWN, not color)
    return any(ahead in board.attacks(enemy) for enemy in enemy_pawns)


def analyze_structure(board: chess.Board, color: chess.Color) -> StructureReport:
    report = StructureReport()
    for square in pawns(board, color):
        if is_isolated(board, square, color):
            report.isolated.append(square)
        if is_doubled(board, square, color):
            report.doubled.append(square)
        if is_backward(board, square, color):
            report.backward.append(square)
        if is_passed(board, square, color):
            report.passed.append(square)
    return report


def _describe(report: StructureReport, side: str) -> list[str]:
    lines = []
    if report.isolated:
        lines.append(f"{side}: peões isolados em {square_list(report.isolated)}.")
    if report.doubled:
        lines.append(f"{side}: peões dobrados em {square_list(report.doubled)}.")
    if report.backward:
        lines.append(f"{side}: peões atrasados em {square_list(report.backward)}.")
    if report.passed:
        lines.append(f"{side}: peões passados em {square_list(report.passed)}.")
    if not lines:
        lines.append(f"{side}: estrutura de peões sadia.")
    return lines


def analyze_pawn_structure(board: chess.Board) -> CriterionResult:
    white = analyze_structure(board, chess.WHITE)
    black = analyze_structure(board, chess.BLACK)

    highlights: dict[chess.Square, str] = {}
    arrows: list[Arrow] = []

    for report in (white, black):
        for square in report.doubled:
            highlights[square] = FILL[WARN]
        for square in report.backward:
            highlights[square] = FILL[WARN]
        for square in report.isolated:
            highlights[square] = FILL[BAD]
        for square in report.passed:
            highlights[square] = FILL[GOOD]

    for report, color in ((white, chess.WHITE), (black, chess.BLACK)):
        for square in report.passed:
            arrows.append(Arrow(square, advance_square(square, color, 2), FILL[GOOD]))

    findings = _describe(white, "Brancas") + _describe(black, "Pretas")

    white_plans: list[str] = []
    black_plans: list[str] = []

    def add_plans(report: StructureReport, mine: list[str], theirs: list[str], side: str) -> None:
        if report.passed:
            mine.append(
                f"Impulsione o(s) peão(ões) passado(s) em {square_list(report.passed)}; "
                "bloqueie-o(s) com um cavalo se for do adversário."
            )
            theirs.append(
                f"Bloqueie o peão passado adversário em {square_list(report.passed)} "
                "com uma peça menor à frente dele."
            )
        if report.isolated:
            mine.append(
                f"Seu peão isolado em {square_list(report.isolated)} pede jogo ativo: "
                "use a casa avançada à frente dele e evite trocas de peças."
            )
            theirs.append(
                f"Pressione o peão isolado em {square_list(report.isolated)}: "
                "troque peças e ataque-o com torres e dama."
            )
        if report.doubled:
            mine.append(
                f"Peões dobrados em {square_list(report.doubled)}: aproveite a coluna semiaberta "
                "resultante para as torres."
            )
            theirs.append(
                f"Fixe os peões dobrados em {square_list(report.doubled)} e ataque-os."
            )
        if report.backward:
            mine.append(
                f"Resolva o peão atrasado em {square_list(report.backward)} avançando-o "
                "com apoio ou trocando-o."
            )
            theirs.append(
                f"Fixe o peão atrasado em {square_list(report.backward)} e dobre torres "
                "na coluna semiaberta à frente dele."
            )
        if not (report.passed or report.isolated or report.doubled or report.backward):
            mine.append(f"{side}: estrutura sólida — busque vantagem por outro critério.")

    add_plans(white, white_plans, black_plans, "Brancas")
    add_plans(black, black_plans, white_plans, "Pretas")

    score = 0.0
    score += 0.10 * (len(white.passed) - len(black.passed))
    score -= 0.08 * (white.weakness_count - black.weakness_count)

    white_weak = white.weakness_count
    black_weak = black.weakness_count
    if white_weak == black_weak and not white.passed and not black.passed:
        verdict = "Estruturas de peões equilibradas."
    elif white_weak < black_weak:
        verdict = "Estrutura de peões melhor para as brancas."
    elif black_weak < white_weak:
        verdict = "Estrutura de peões melhor para as pretas."
    else:
        verdict = "Estruturas com fraquezas equivalentes, mas há peões passados em jogo."

    metrics = [
        Metric("Isolados (B x P)", f"{len(white.isolated)} x {len(black.isolated)}"),
        Metric("Dobrados (B x P)", f"{len(white.doubled)} x {len(black.doubled)}"),
        Metric("Atrasados (B x P)", f"{len(white.backward)} x {len(black.backward)}"),
        Metric("Passados (B x P)", f"{len(white.passed)} x {len(black.passed)}"),
    ]

    return CriterionResult(
        key="pawn_structure",
        title="Estrutura básica de peões",
        icon=":material/view_column:",
        verdict=verdict,
        score=clamp(score),
        metrics=metrics,
        findings=findings,
        white_plans=white_plans,
        black_plans=black_plans,
        highlights=highlights,
        arrows=arrows,
    )

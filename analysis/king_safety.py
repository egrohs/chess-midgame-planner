"""Critério 10 — Segurança do rei: escudo, linhas expostas, pressão e fugas.

O escudo e as linhas abertas só são penalizados quando o adversário ainda tem
peças capazes de atacar. As fugas são casas adjacentes seguras para o rei,
independentemente de quem tem o lance; não são um diagnóstico de xeque-mate.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import chess

from analysis.board_utils import relative_rank, square_list
from analysis.types import BAD, FILL, GOOD, INFO, WARN, Arrow, CriterionResult, Metric, clamp

ATTACKING_PIECES = (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN)


@dataclass
class KingSafetyReport:
    king: chess.Square
    shield: list[chess.Square] = field(default_factory=list)
    missing_shield: list[chess.Square] = field(default_factory=list)
    exposed_files: list[int] = field(default_factory=list)
    attackers: set[chess.Square] = field(default_factory=set)
    pressured: list[chess.Square] = field(default_factory=list)
    escapes: list[chess.Square] = field(default_factory=list)
    in_check: bool = False
    danger: float = 0.0


def _king_escapes(board: chess.Board, color: chess.Color, king: chess.Square) -> list[chess.Square]:
    """Verifica destinos após mover o rei, inclusive capturas e ataques descobertos."""
    escapes = []
    for target in board.attacks(king):
        occupant = board.piece_at(target)
        if occupant is not None and (occupant.color == color or occupant.piece_type == chess.KING):
            continue
        after = board.copy(stack=False)
        after.remove_piece_at(king)
        after.set_piece_at(target, chess.Piece(chess.KING, color))
        if not after.is_attacked_by(not color, target):
            escapes.append(target)
    return sorted(escapes)


def analyze_king_safety_for(board: chess.Board, color: chess.Color) -> KingSafetyReport:
    king = board.king(color)
    if king is None:
        raise ValueError("A posição precisa ter os dois reis para analisar a segurança.")
    report = KingSafetyReport(king=king)
    enemy = not color
    report.escapes = _king_escapes(board, color, king)
    report.in_check = board.is_attacked_by(enemy, king)

    zone = set(board.attacks(king))
    zone.add(king)
    for target in zone:
        sources = {
            source for source in board.attackers(enemy, target)
            if board.piece_type_at(source) != chess.KING
        }
        if sources:
            report.pressured.append(target)
            report.attackers.update(sources)
    report.pressured.sort()

    if any(board.pieces(piece_type, enemy) for piece_type in ATTACKING_PIECES):
        rank = chess.square_rank(king)
        direction = 1 if color == chess.WHITE else -1
        files = range(
            max(0, chess.square_file(king) - 1),
            min(7, chess.square_file(king) + 1) + 1,
        )
        if relative_rank(king, color) <= 1:
            for file_index in files:
                front = chess.square(file_index, rank + direction)
                farther = chess.square(file_index, rank + 2 * direction)
                if board.piece_at(front) == chess.Piece(chess.PAWN, color):
                    report.shield.append(front)
                elif board.piece_at(farther) == chess.Piece(chess.PAWN, color):
                    report.shield.append(farther)
                else:
                    report.missing_shield.append(front)

        if any(board.pieces(piece_type, enemy) for piece_type in (chess.ROOK, chess.QUEEN)):
            for file_index in files:
                if not board.pieces(chess.PAWN, color) & chess.BB_FILES[file_index]:
                    report.exposed_files.append(file_index)

    # Pressão real pesa mais que exposição potencial; ausência de fugas só
    # agrava a situação se há atacantes, pois pode ser normal atrás do escudo.
    report.danger = (
        len(report.missing_shield) * 0.7
        + len(report.exposed_files) * 0.6
        + len(report.attackers) * 0.8
        + len(report.pressured) * 0.25
        + (2.0 if report.in_check else 0.0)
        + (0.8 if report.attackers and not report.escapes else 0.0)
    )
    return report


def analyze_king_safety(board: chess.Board) -> CriterionResult:
    white = analyze_king_safety_for(board, chess.WHITE)
    black = analyze_king_safety_for(board, chess.BLACK)
    score = clamp((black.danger - white.danger) / 8.0)

    if abs(score) <= 0.05:
        verdict = "Reis com segurança semelhante."
    elif score > 0:
        verdict = "Rei branco mais seguro; rei preto sob maior pressão."
    else:
        verdict = "Rei preto mais seguro; rei branco sob maior pressão."

    highlights: dict[chess.Square, str] = {}
    arrows: list[Arrow] = []
    for report, safe_fill in ((white, GOOD), (black, BAD)):
        highlights[report.king] = FILL[WARN] if report.in_check else FILL[safe_fill]
        for square in report.shield:
            highlights[square] = FILL[safe_fill]
        for square in report.missing_shield:
            highlights[square] = FILL[WARN]
        for square in report.escapes:
            highlights.setdefault(square, FILL[INFO])
        for source in report.attackers:
            target = min(
                (square for square in report.pressured if square in board.attacks(source)),
                key=lambda square: chess.square_distance(square, report.king),
            )
            arrows.append(Arrow(source, target, FILL[WARN]))

    def describe(report: KingSafetyReport, side: str) -> list[str]:
        lines = [
            f"{side}: rei em {chess.square_name(report.king)}; "
            f"escudo {len(report.shield)}/{len(report.shield) + len(report.missing_shield)}; "
            f"{len(report.attackers)} atacantes na zona do rei."
        ]
        if report.exposed_files:
            lines.append(
                f"{side}: sem peão próprio nas colunas próximas "
                f"{', '.join(chess.FILE_NAMES[file_index] for file_index in report.exposed_files)}."
            )
        if report.pressured:
            lines.append(f"{side}: casas da zona sob ataque em {square_list(report.pressured)}.")
        lines.append(
            f"{side}: {len(report.escapes)} fugas seguras"
            + (f" ({square_list(report.escapes)})." if report.escapes else ".")
        )
        return lines

    def plans(mine: KingSafetyReport, theirs: KingSafetyReport) -> list[str]:
        actions = []
        if mine.in_check:
            actions.append("Responda ao xeque antes de seguir qualquer plano posicional.")
        if mine.missing_shield or mine.exposed_files:
            actions.append(
                "Reforce o abrigo do rei e evite abrir mais colunas próximas "
                "enquanto houver peças atacantes adversárias."
            )
        if mine.attackers:
            actions.append(
                "Troque ou afaste as peças que pressionam a zona do rei; "
                "crie uma casa de fuga segura quando possível."
            )
        if theirs.attackers or theirs.missing_shield or theirs.exposed_files:
            actions.append(
                "Explore as fragilidades do rei adversário com peças coordenadas, "
                "confirmando taticamente cada ameaça."
            )
        if not actions:
            actions.append("Mantenha o escudo de peões e não abra linhas contra seu rei.")
        return actions

    return CriterionResult(
        key="king_safety",
        title="Segurança do rei",
        icon=":material/shield:",
        verdict=verdict,
        score=score,
        metrics=[
            Metric("Escudo (B x P)", f"{len(white.shield)}/{len(white.shield) + len(white.missing_shield)} x "
                   f"{len(black.shield)}/{len(black.shield) + len(black.missing_shield)}"),
            Metric("Colunas sem peão (B x P)", f"{len(white.exposed_files)} x {len(black.exposed_files)}"),
            Metric("Atacantes (B x P)", f"{len(white.attackers)} x {len(black.attackers)}"),
            Metric("Fugas seguras (B x P)", f"{len(white.escapes)} x {len(black.escapes)}"),
        ],
        findings=describe(white, "Brancas") + describe(black, "Pretas"),
        white_plans=plans(white, black),
        black_plans=plans(black, white),
        highlights=highlights,
        arrows=arrows,
    )

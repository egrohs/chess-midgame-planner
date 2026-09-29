"""Critério 4 — Centro aberto, fechado, fixo ou dinâmico."""

from __future__ import annotations

import chess

from analysis.board_utils import CENTER_SQUARES, FILE_NAMES, forward_square
from analysis.types import FILL, INFO, NEUTRAL, WARN, CriterionResult, Metric

CENTER_FILES = (3, 4)  # d, e
EXTENDED_FILES = (2, 3, 4, 5)  # c-f

CENTER_TYPES = {
    "open": "Centro aberto",
    "closed": "Centro fechado",
    "fixed": "Centro fixo (tensão resolvida)",
    "dynamic": "Centro dinâmico / em tensão",
}


def center_pawns(board: chess.Board, color: chess.Color) -> list[chess.Square]:
    return [
        sq
        for sq in board.pieces(chess.PAWN, color)
        if chess.square_file(sq) in CENTER_FILES
    ]


def locked_pairs(board: chess.Board) -> list[tuple[chess.Square, chess.Square]]:
    """Pares de peões centrais que se bloqueiam frontalmente."""
    pairs = []
    for square in center_pawns(board, chess.WHITE):
        ahead = forward_square(square, chess.WHITE)
        if ahead is None:
            continue
        piece = board.piece_at(ahead)
        if piece is not None and piece.piece_type == chess.PAWN and piece.color == chess.BLACK:
            pairs.append((square, ahead))
    return pairs


def center_tension(board: chess.Board) -> list[tuple[chess.Square, chess.Square]]:
    """Peões centrais que podem se capturar mutuamente."""
    tension = []
    for square in center_pawns(board, chess.WHITE):
        for target in board.attacks(square):
            piece = board.piece_at(target)
            if piece is not None and piece.piece_type == chess.PAWN and piece.color == chess.BLACK:
                tension.append((square, target))
    for square in center_pawns(board, chess.BLACK):
        for target in board.attacks(square):
            piece = board.piece_at(target)
            if piece is not None and piece.piece_type == chess.PAWN and piece.color == chess.WHITE:
                tension.append((square, target))
    return tension


def classify_center(board: chess.Board) -> str:
    white_center = center_pawns(board, chess.WHITE)
    black_center = center_pawns(board, chess.BLACK)
    total = len(white_center) + len(black_center)
    locked = locked_pairs(board)
    tension = center_tension(board)

    # Duas ou mais cadeias travadas caracterizam um centro realmente fechado
    # (ex.: Francesa do avanço, Índia do Rei). Um único par travado — como e4/e5
    # na Italiana — apenas fixa o centro.
    if len(locked) >= 2:
        return "closed"
    if tension:
        return "dynamic"
    if locked:
        return "fixed"
    if total <= 1:
        return "open"
    # Sem contato entre peões e um dos lados sem peões centrais: linhas livres.
    if not white_center or not black_center:
        return "open"
    if total == 2:
        return "fixed"
    return "dynamic"


def analyze_center(board: chess.Board) -> CriterionResult:
    white_center = center_pawns(board, chess.WHITE)
    black_center = center_pawns(board, chess.BLACK)
    locked = locked_pairs(board)
    tension = center_tension(board)
    kind = classify_center(board)

    highlights: dict[chess.Square, str] = {}
    for square in CENTER_SQUARES:
        highlights[square] = FILL[NEUTRAL]
    for white_sq, black_sq in locked:
        highlights[white_sq] = FILL[WARN]
        highlights[black_sq] = FILL[WARN]
    for attacker, target in tension:
        highlights[attacker] = FILL[INFO]
        highlights[target] = FILL[INFO]

    occupied_center = [sq for sq in CENTER_SQUARES if board.piece_at(sq) is not None]
    open_files = [
        f
        for f in EXTENDED_FILES
        if not any(
            chess.square_file(sq) == f
            for sq in list(board.pieces(chess.PAWN, chess.WHITE))
            + list(board.pieces(chess.PAWN, chess.BLACK))
        )
    ]

    findings = [
        f"Peões centrais (colunas d/e): brancas {len(white_center)} x pretas {len(black_center)}.",
        f"Casas centrais ocupadas: {len(occupied_center)} de 4.",
    ]
    if locked:
        findings.append(
            "Cadeias travadas: "
            + ", ".join(f"{chess.square_name(w)}/{chess.square_name(b)}" for w, b in locked)
            + "."
        )
    if tension:
        findings.append(f"Tensão central em {len(tension)} contato(s) de peões.")
    if open_files:
        findings.append(
            "Colunas abertas no centro ampliado: "
            + ", ".join(FILE_NAMES[f] for f in open_files)
            + "."
        )

    white_plans: list[str] = []
    black_plans: list[str] = []

    if kind == "closed":
        shared = [
            "Centro fechado: jogue nas alas, avançando peões na ala onde tiver espaço.",
            "Manobre os cavalos por trás da cadeia; eles valem mais que os bispos aqui.",
            "Ataque a base da cadeia de peões adversária.",
        ]
        white_plans += shared
        black_plans += shared
    elif kind == "open":
        shared = [
            "Centro aberto: dispute as colunas abertas com as torres.",
            "Priorize segurança do rei e atividade de peças; evite jogadas lentas de peão.",
            "Valorize os bispos — as diagonais longas estão livres.",
        ]
        white_plans += shared
        black_plans += shared
    elif kind == "fixed":
        shared = [
            "Centro fixo: identifique as casas fracas fixadas e ocupe-as com cavalos.",
            "Prepare uma ruptura lateral (c ou f) para abrir linhas no momento certo.",
        ]
        white_plans += shared
        black_plans += shared
    else:
        shared = [
            "Centro em tensão: decida entre manter a tensão, capturar ou avançar.",
            "Antes de resolver a tensão, melhore a pior peça — quem resolve primeiro cede opções.",
        ]
        white_plans += shared
        black_plans += shared

    space = len(white_center) - len(black_center)
    if space > 0:
        white_plans.append("Você tem mais peões centrais: ganhe espaço e restrinja as peças pretas.")
    elif space < 0:
        black_plans.append(
            "Você tem mais peões centrais: ganhe espaço e restrinja as peças brancas."
        )

    metrics = [
        Metric("Tipo de centro", CENTER_TYPES[kind]),
        Metric("Peões centrais", f"{len(white_center)} x {len(black_center)}"),
        Metric("Contatos em tensão", str(len(tension))),
    ]

    return CriterionResult(
        key="center",
        title="Centro aberto/fechado",
        icon=":material/grid_view:",
        verdict=CENTER_TYPES[kind] + ".",
        score=0.12 * space,
        metrics=metrics,
        findings=findings,
        white_plans=white_plans,
        black_plans=black_plans,
        highlights=highlights,
    )

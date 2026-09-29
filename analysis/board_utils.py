"""Utilitários de baixo nível reutilizados pelos critérios."""

from __future__ import annotations

import chess

FILE_NAMES = "abcdefgh"

QUEENSIDE_FILES = (0, 1, 2)  # a, b, c
CENTER_FILES = (3, 4)  # d, e
KINGSIDE_FILES = (5, 6, 7)  # f, g, h

WING_FILES = {
    "queenside": QUEENSIDE_FILES,
    "center": CENTER_FILES,
    "kingside": KINGSIDE_FILES,
}

WING_LABELS = {
    "queenside": "ala da dama (a-c)",
    "center": "centro (d-e)",
    "kingside": "ala do rei (f-h)",
}

CENTER_SQUARES = (chess.D4, chess.E4, chess.D5, chess.E5)

MINOR_HOME_SQUARES = {
    chess.WHITE: (chess.B1, chess.C1, chess.F1, chess.G1),
    chess.BLACK: (chess.B8, chess.C8, chess.F8, chess.G8),
}

ROOK_HOME_SQUARES = {
    chess.WHITE: (chess.A1, chess.H1),
    chess.BLACK: (chess.A8, chess.H8),
}

QUEEN_HOME_SQUARE = {chess.WHITE: chess.D1, chess.BLACK: chess.D8}
KING_HOME_SQUARE = {chess.WHITE: chess.E1, chess.BLACK: chess.E8}
BACK_RANK = {chess.WHITE: 0, chess.BLACK: 7}


def pawns(board: chess.Board, color: chess.Color) -> list[chess.Square]:
    return sorted(board.pieces(chess.PAWN, color))


def pawn_files(board: chess.Board, color: chess.Color) -> list[int]:
    return [chess.square_file(sq) for sq in pawns(board, color)]


def pawns_on_file(board: chess.Board, color: chess.Color, file_index: int) -> list[chess.Square]:
    return [sq for sq in pawns(board, color) if chess.square_file(sq) == file_index]


def forward_square(square: chess.Square, color: chess.Color) -> chess.Square | None:
    """Casa imediatamente à frente do peão, ou ``None`` se estiver na borda."""
    rank = chess.square_rank(square)
    target = rank + 1 if color == chess.WHITE else rank - 1
    if not 0 <= target <= 7:
        return None
    return chess.square(chess.square_file(square), target)


def advance_square(square: chess.Square, color: chess.Color, steps: int) -> chess.Square:
    """Avança ``steps`` casas, saturando na última fileira."""
    rank = chess.square_rank(square)
    target = rank + steps if color == chess.WHITE else rank - steps
    target = max(0, min(7, target))
    return chess.square(chess.square_file(square), target)


def relative_rank(square: chess.Square, color: chess.Color) -> int:
    """Fileira do ponto de vista da cor (0 = casa inicial da torre)."""
    rank = chess.square_rank(square)
    return rank if color == chess.WHITE else 7 - rank


def most_advanced(squares: list[chess.Square], color: chess.Color) -> chess.Square | None:
    if not squares:
        return None
    return max(squares, key=lambda sq: relative_rank(sq, color))


def square_list(squares) -> str:
    return ", ".join(chess.square_name(sq) for sq in sorted(squares))


def has_castled(board: chess.Board, color: chess.Color) -> bool:
    """Heurística: rei já abrigado numa das alas, ainda na fileira inicial."""
    king_square = board.king(color)
    if king_square is None:
        return False
    file_index = chess.square_file(king_square)
    on_back_rank = chess.square_rank(king_square) == BACK_RANK[color]
    return on_back_rank and file_index in (1, 2, 6, 7)


def king_moved(board: chess.Board, color: chess.Color) -> bool:
    """Indica se o rei já saiu da casa inicial (perda do direito ao roque natural)."""
    king_square = board.king(color)
    return king_square is not None and king_square != KING_HOME_SQUARE[color]


def rooks_connected(board: chess.Board, color: chess.Color) -> bool:
    """Duas torres na mesma linha ou coluna sem peças entre elas."""
    rooks = sorted(board.pieces(chess.ROOK, color))
    if len(rooks) < 2:
        return False
    for index, first in enumerate(rooks):
        for second in rooks[index + 1 :]:
            same_line = chess.square_rank(first) == chess.square_rank(second) or chess.square_file(
                first
            ) == chess.square_file(second)
            if not same_line:
                continue
            if not (chess.SquareSet.between(first, second) & chess.SquareSet(board.occupied)):
                return True
    return False

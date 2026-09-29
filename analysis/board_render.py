"""Renderização do tabuleiro com indicadores visuais."""

from __future__ import annotations

import chess
import chess.svg

from analysis.types import CriterionResult

BOARD_COLORS = {
    "square light": "#eeeed2",
    "square dark": "#769656",
    "margin": "#312e2b",
    "coord": "#e8e8e8",
}


def render_board(
    board: chess.Board,
    *,
    results: list[CriterionResult] | None = None,
    orientation: chess.Color = chess.WHITE,
    size: int = 480,
) -> str:
    """Gera o SVG do tabuleiro aplicando destaques e setas dos critérios ativos."""
    fill: dict[chess.Square, str] = {}
    arrows: list[chess.svg.Arrow] = []

    for result in results or []:
        fill.update(result.highlights)
        arrows.extend(
            chess.svg.Arrow(arrow.tail, arrow.head, color=arrow.color)
            for arrow in result.arrows
            if arrow.tail != arrow.head
        )

    check_square = board.king(board.turn) if board.is_check() else None

    return chess.svg.board(
        board,
        orientation=orientation,
        fill=fill,
        arrows=arrows,
        check=check_square,
        colors=BOARD_COLORS,
        size=size,
    )

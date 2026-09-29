"""Renderização do tabuleiro com indicadores visuais."""

from __future__ import annotations

import chess
import chess.svg

from analysis.types import CriterionResult

BOARD_COLORS = {
    "square light": "#eeeed2",
    "square dark": "#769656",
    "square light lastmove": "#f6f669",
    "square dark lastmove": "#baca44",
    "margin": "#312e2b",
    "coord": "#e8e8e8",
}

SELECTED_FILL = "#f2c14e99"
TARGET_FILL = "#3d85c699"
CAPTURE_FILL = "#c6282899"


def move_hints(board: chess.Board, selected: chess.Square | None) -> dict[chess.Square, str]:
    """Pinta a casa selecionada e os destinos legais a partir dela."""
    if selected is None:
        return {}
    hints: dict[chess.Square, str] = {selected: SELECTED_FILL}
    for move in board.legal_moves:
        if move.from_square != selected:
            continue
        hints[move.to_square] = CAPTURE_FILL if board.is_capture(move) else TARGET_FILL
    return hints


def render_board(
    board: chess.Board,
    *,
    results: list[CriterionResult] | None = None,
    orientation: chess.Color = chess.WHITE,
    size: int = 480,
    extra_fill: dict[chess.Square, str] | None = None,
    lastmove: chess.Move | None = None,
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

    # Os destaques de interação têm prioridade sobre os dos critérios.
    if extra_fill:
        fill.update(extra_fill)

    check_square = board.king(board.turn) if board.is_check() else None

    return chess.svg.board(
        board,
        orientation=orientation,
        fill=fill,
        arrows=arrows,
        check=check_square,
        lastmove=lastmove,
        colors=BOARD_COLORS,
        size=size,
    )

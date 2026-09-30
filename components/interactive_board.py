"""Tabuleiro de xadrez clicável (Streamlit Custom Component v2)."""

from __future__ import annotations

from collections.abc import Callable

import chess
import chess.svg

import streamlit as st

# Geometria do SVG gerado por ``chess.svg.board`` com os parâmetros padrão
# (coordinates=True, borders=False): margem de 15 e casas de 45 unidades.
SQUARE_SIZE = chess.svg.SQUARE_SIZE
BOARD_MARGIN = 15
FULL_SIZE = 2 * BOARD_MARGIN + 8 * SQUARE_SIZE

HTML = """
<div class="cmp-wrap">
  <div class="cmp-board"></div>
  <div class="cmp-grid"></div>
</div>
"""

CSS = """
.cmp-wrap {
  position: relative;
  width: 100%;
  max-width: var(--cmp-size, 480px);
  margin: 0 auto;
  aspect-ratio: 1 / 1;
  user-select: none;
}
.cmp-board, .cmp-board svg {
  width: 100%;
  height: 100%;
  display: block;
}
.cmp-grid {
  position: absolute;
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  grid-template-rows: repeat(8, 1fr);
}
.cmp-cell {
  cursor: pointer;
  border: 2px solid transparent;
  border-radius: 2px;
  transition: border-color 90ms ease-in-out, background-color 90ms ease-in-out;
}
.cmp-cell:hover {
  border-color: var(--st-primary-color, #769656);
  background-color: color-mix(in srgb, var(--st-primary-color, #769656) 18%, transparent);
}
.cmp-cell:focus-visible {
  outline: 2px solid var(--st-primary-color, #769656);
  outline-offset: -2px;
}
.cmp-cell[data-selected="true"] {
  border-color: var(--st-primary-color, #769656);
  background-color: color-mix(in srgb, var(--st-primary-color, #769656) 30%, transparent);
}
.cmp-wrap[data-readonly="true"] .cmp-cell {
  cursor: default;
}
.cmp-wrap[data-readonly="true"] .cmp-cell:hover {
  border-color: transparent;
  background-color: transparent;
}
"""

JS = """
const FILES = "abcdefgh"

export default function (component) {
  const { data, parentElement, setTriggerValue } = component

  const wrap = parentElement.querySelector(".cmp-wrap")
  const boardHost = parentElement.querySelector(".cmp-board")
  const grid = parentElement.querySelector(".cmp-grid")
  if (!wrap || !boardHost || !grid) return

  const svg = data?.svg ?? ""
  const orientation = data?.orientation === "black" ? "black" : "white"
  const readonly = Boolean(data?.readonly)
  const allowDrag = Boolean(data?.allow_drag)
  const selected = data?.selected ?? null
  const offsetPct = Number(data?.offset_pct ?? 0)
  const boardPct = 100 - 2 * offsetPct

  if (boardHost.dataset.svg !== svg) {
    boardHost.innerHTML = svg
    boardHost.dataset.svg = svg
  }

  wrap.style.setProperty("--cmp-size", `${Number(data?.size ?? 480)}px`)
  wrap.dataset.readonly = String(readonly)

  grid.style.left = `${offsetPct}%`
  grid.style.top = `${offsetPct}%`
  grid.style.width = `${boardPct}%`
  grid.style.height = `${boardPct}%`

  // Ordem de leitura do grid: da casa superior esquerda para a inferior direita,
  // respeitando a orientação escolhida.
  const squares = []
  for (let row = 0; row < 8; row++) {
    for (let col = 0; col < 8; col++) {
      const file = orientation === "white" ? col : 7 - col
      const rank = orientation === "white" ? 7 - row : row
      squares.push(`${FILES[file]}${rank + 1}`)
    }
  }

  if (grid.dataset.layout !== squares.join(",")) {
    grid.replaceChildren()
    for (const name of squares) {
      const cell = document.createElement("div")
      cell.className = "cmp-cell"
      cell.dataset.square = name
      cell.setAttribute("role", "button")
      cell.setAttribute("tabindex", "0")
      cell.setAttribute("aria-label", name)
      grid.appendChild(cell)
    }
    grid.dataset.layout = squares.join(",")
  }

  for (const cell of grid.children) {
    cell.dataset.selected = String(cell.dataset.square === selected)
    cell.draggable = allowDrag && !readonly
  }

  const emit = (name) => {
    if (readonly) return
    setTriggerValue("square", { square: name, nonce: Date.now() })
  }

  let draggedSquare = null
  let suppressClickUntil = 0

  grid.onclick = (event) => {
    if (Date.now() < suppressClickUntil) return
    const cell = event.target.closest(".cmp-cell")
    if (cell) emit(cell.dataset.square)
  }

  grid.ondragstart = (event) => {
    const cell = event.target.closest(".cmp-cell")
    if (!allowDrag || readonly || !cell) {
      event.preventDefault()
      return
    }
    draggedSquare = cell.dataset.square
    if (event.dataTransfer) {
      event.dataTransfer.setData("text/plain", draggedSquare)
      event.dataTransfer.effectAllowed = "move"
    }
  }

  grid.ondragover = (event) => {
    if (draggedSquare && event.target.closest(".cmp-cell")) event.preventDefault()
  }

  grid.ondrop = (event) => {
    const cell = event.target.closest(".cmp-cell")
    if (!draggedSquare || !cell) return
    event.preventDefault()
    const from = event.dataTransfer?.getData("text/plain") || draggedSquare
    const to = cell.dataset.square
    if (from !== to) {
      setTriggerValue("square", { from, to, nonce: Date.now() })
      suppressClickUntil = Date.now() + 400
    }
    draggedSquare = null
  }

  grid.ondragend = () => {
    draggedSquare = null
  }

  grid.onkeydown = (event) => {
    if (event.key !== "Enter" && event.key !== " ") return
    const cell = event.target.closest(".cmp-cell")
    if (!cell) return
    event.preventDefault()
    emit(cell.dataset.square)
  }

  return () => {
    grid.onclick = null
    grid.ondragstart = null
    grid.ondragover = null
    grid.ondrop = null
    grid.ondragend = null
    grid.onkeydown = null
  }
}
"""

def _register():
    """Registra o componente. O Streamlit limpa o registro a cada execução do script,
    por isso o registro acontece junto com a montagem, e não só na importação."""
    return st.components.v2.component(
        "chess_interactive_board",
        html=HTML,
        css=CSS,
        js=JS,
    )


def interactive_board(
    svg: str,
    *,
    key: str,
    orientation: chess.Color = chess.WHITE,
    selected: chess.Square | None = None,
    size: int = 480,
    readonly: bool = False,
    allow_drag: bool = True,
    on_square_change: Callable[[], None] | None = None,
):
    """Mostra o tabuleiro e devolve a casa clicada em ``result.square``."""
    if on_square_change is None:

        def on_square_change() -> None:
            return None

    return _register()(
        key=key,
        data={
            "svg": svg,
            "orientation": "white" if orientation == chess.WHITE else "black",
            "selected": chess.square_name(selected) if selected is not None else None,
            "offset_pct": 100 * BOARD_MARGIN / FULL_SIZE,
            "size": size,
            "readonly": readonly,
            "allow_drag": allow_drag,
        },
        on_square_change=on_square_change,
    )

"""Chess Midgame Planner — análise posicional e plano de jogo."""

from __future__ import annotations

import chess

import streamlit as st
from analysis import (
    analyze_position,
    balance_label,
    build_plan,
    move_hints,
    overall_score,
    render_board,
    summary_line,
)
from components import interactive_board
from game import (
    GameLine,
    clear_board,
    handle_play_click,
    handle_setup_click,
    line_from_fen,
    line_from_pgn,
    position_problems,
    set_turn,
)
from presets import DEFAULT_PRESET, PRESETS

st.set_page_config(
    page_title="Chess Midgame Planner",
    page_icon=":material/strategy:",
    layout="wide",
)

BOARD_KEY = "board_component"
PLAY_MODE = "Mover peças"
SETUP_MODE = "Montar posição"

LAYER_LABELS = {
    "material": "Material",
    "pawn_majority": "Maiorias",
    "development": "Desenvolvimento",
    "center": "Centro",
    "pawn_structure": "Estrutura",
    "weak_squares": "Casas fracas",
    "outposts": "Outposts",
    "space": "Espaço",
    "piece_activity": "Atividade",
    "king_safety": "Segurança do rei",
    "worst_piece": "Pior peça",
}

STANCE_ICONS = {
    "explorar": ":material/trending_up:",
    "neutralizar": ":material/shield:",
    "equilibrado": ":material/balance:",
}

PROMOTION_PIECES = {
    chess.QUEEN: "Dama",
    chess.ROOK: "Torre",
    chess.BISHOP: "Bispo",
    chess.KNIGHT: "Cavalo",
}

SETUP_PALETTE = {
    "K": "♔",
    "Q": "♕",
    "R": "♖",
    "B": "♗",
    "N": "♘",
    "P": "♙",
    "k": "♚",
    "q": "♛",
    "r": "♜",
    "b": "♝",
    "n": "♞",
    "p": "♟",
    "erase": "⌫",
}

# --- Estado ------------------------------------------------------------------

for name, value in {
    "line": GameLine(root_fen=PRESETS[DEFAULT_PRESET]),
    "mode": PLAY_MODE,
    "selected": None,
    "setup_piece": "P",
    "promotion": chess.QUEEN,
    "preset": DEFAULT_PRESET,
    "status": None,
}.items():
    st.session_state.setdefault(name, value)


def set_line(line: GameLine) -> None:
    st.session_state.line = line
    st.session_state.selected = None


def on_preset_change() -> None:
    set_line(GameLine(root_fen=PRESETS[st.session_state.preset]))
    st.session_state.status = None


def on_mode_change() -> None:
    """Ao entrar no modo de edição, congela a posição atual como nova raiz."""
    st.session_state.selected = None
    line: GameLine = st.session_state.line
    if st.session_state.mode == SETUP_MODE and line.moves:
        set_line(GameLine(root_fen=line.board.fen()))


def on_setup_turn_change() -> None:
    line: GameLine = st.session_state.line
    turn = chess.WHITE if st.session_state.setup_turn == "Brancas" else chess.BLACK
    set_line(GameLine(root_fen=set_turn(line.root_fen, turn)))


def on_ply_change() -> None:
    st.session_state.line.goto(int(st.session_state.ply_slider))
    st.session_state.selected = None


def apply_setup_click(line: GameLine, square: chess.Square) -> None:
    symbol = st.session_state.setup_piece
    if symbol not in SETUP_PALETTE:
        st.session_state.status = ("error", "Selecione uma peça na paleta antes de editar o tabuleiro.")
        return
    set_line(handle_setup_click(line, square, symbol))
    st.session_state.status = None


def apply_play_click(line: GameLine, square: chess.Square) -> None:
    before = line.length
    st.session_state.selected = handle_play_click(
        line, st.session_state.selected, square, promotion=st.session_state.promotion
    )
    if line.length != before:
        st.session_state.status = None


def on_square_click() -> None:
    """Callback do componente: roda antes do corpo do script."""
    payload = getattr(st.session_state.get(BOARD_KEY), "square", None)
    name = payload.get("square") if isinstance(payload, dict) else None
    if not name:
        return

    square = chess.parse_square(name)
    line: GameLine = st.session_state.line
    if st.session_state.mode == SETUP_MODE:
        apply_setup_click(line, square)
    else:
        apply_play_click(line, square)


# --- Barra lateral -----------------------------------------------------------

def sync_fen_input() -> None:
    """Espelha o FEN da posição atual no campo de texto.

    O widget tem ``key``, então o Streamlit ignora ``value=`` nos reruns e
    mantém o valor guardado no ``session_state``. Só sobrescrevemos quando o
    valor exibido ainda é o último FEN que sincronizamos — assim não apagamos
    um FEN que o usuário esteja digitando.
    """
    current = st.session_state.line.board.fen()
    shown = st.session_state.get("fen_input")
    last_synced = st.session_state.get("_fen_synced")
    if shown is None or shown == last_synced:
        st.session_state.fen_input = current
    st.session_state._fen_synced = current


with st.sidebar:
    st.subheader("Posição")
    st.selectbox("Exemplos", list(PRESETS), key="preset", on_change=on_preset_change)

    sync_fen_input()

    with st.form("fen_form", border=False):
        fen_text = st.text_area("Carregar FEN", height=90, key="fen_input")
        if st.form_submit_button("Aplicar FEN", icon=":material/input:"):
            try:
                set_line(line_from_fen(fen_text))
                st.session_state.status = ("success", "FEN carregado.")
                st.rerun()
            except ValueError as exc:
                st.session_state.status = ("error", f"FEN inválido: {exc}")

    with st.form("pgn_form", border=False):
        pgn_text = st.text_area(
            "Carregar PGN", height=120, placeholder="1. e4 e5 2. Nf3 Nc6 ...", key="pgn_input"
        )
        if st.form_submit_button("Aplicar PGN", icon=":material/description:"):
            try:
                set_line(line_from_pgn(pgn_text))
                st.session_state.status = ("success", "PGN carregado.")
                st.rerun()
            except ValueError as exc:
                st.session_state.status = ("error", f"PGN inválido: {exc}")

    st.subheader("Visualização")
    orientation_label = st.segmented_control(
        "Orientação do tabuleiro", ["Brancas", "Pretas"], default="Brancas"
    )
    board_size = st.slider("Tamanho do tabuleiro", 320, 720, 480, step=40)

orientation = chess.BLACK if orientation_label == "Pretas" else chess.WHITE

# --- Cabeçalho ---------------------------------------------------------------

st.title(":material/strategy: Chess Midgame Planner")
st.caption(
    "Clique no tabuleiro para jogar ou montar a posição, navegue pelos lances "
    "e veja o plano sugerido pelos critérios posicionais."
)

if st.session_state.status:
    kind, message = st.session_state.status
    (st.success if kind == "success" else st.error)(message, icon=":material/info:")

line: GameLine = st.session_state.line
problems = position_problems(line.root_fen)

board_col, info_col = st.columns([1.05, 1], gap="large")

with board_col:
    st.segmented_control("Modo", [PLAY_MODE, SETUP_MODE], key="mode", on_change=on_mode_change)

    board_slot = st.container()

    if st.session_state.mode == SETUP_MODE:
        st.segmented_control(
            "Peça a colocar",
            list(SETUP_PALETTE),
            format_func=lambda symbol: SETUP_PALETTE[symbol],
            key="setup_piece",
            required=True,
        )
        st.caption("Clique numa casa para colocar a peça; clique de novo na mesma peça para apagar.")

        # O widget espelha o lado que tem o lance na posição atual.
        st.session_state["setup_turn"] = (
            "Brancas" if line.board.turn == chess.WHITE else "Pretas"
        )
        with st.container(horizontal=True):
            st.segmented_control(
                "Lance de", ["Brancas", "Pretas"], key="setup_turn", on_change=on_setup_turn_change
            )
            if st.button("Limpar tabuleiro", icon=":material/delete:", key="setup_clear"):
                set_line(GameLine(root_fen=clear_board(line.board.turn)))
                st.rerun()
            if st.button("Posição inicial", icon=":material/restart_alt:", key="setup_start"):
                set_line(GameLine(root_fen=chess.STARTING_FEN))
                st.rerun()
    else:
        with st.container(horizontal=True):
            if st.button(
                "", icon=":material/first_page:", help="Início", disabled=line.ply == 0,
                key="nav_first",
            ):
                line.goto(0)
                st.session_state.selected = None
            if st.button(
                "", icon=":material/chevron_left:", help="Anterior", disabled=line.ply == 0,
                key="nav_prev",
            ):
                line.step(-1)
                st.session_state.selected = None
            if st.button(
                "",
                icon=":material/chevron_right:",
                help="Próximo",
                disabled=line.ply >= line.length,
                key="nav_next",
            ):
                line.step(1)
                st.session_state.selected = None
            if st.button(
                "", icon=":material/last_page:", help="Fim", disabled=line.ply >= line.length,
                key="nav_last",
            ):
                line.goto(line.length)
                st.session_state.selected = None
            if st.button(
                "", icon=":material/undo:", help="Desfazer lance", disabled=not line.moves,
                key="nav_undo",
            ):
                line.undo()
                st.session_state.selected = None

        if line.length:
            st.session_state["ply_slider"] = line.ply
            st.slider("Lance", 0, line.length, key="ply_slider", on_change=on_ply_change)

        st.selectbox(
            "Peça de promoção",
            list(PROMOTION_PIECES),
            format_func=lambda piece: PROMOTION_PIECES[piece],
            key="promotion",
        )

    # Recalculado após os controles para refletir navegação e edição.
    board = line.board
    selected = st.session_state.selected
    if selected is not None and st.session_state.mode == PLAY_MODE:
        piece = board.piece_at(selected)
        if piece is None or piece.color != board.turn:
            selected = st.session_state.selected = None

    results = [] if problems else analyze_position(board)
    score = overall_score(results) if results else 0.0

    active_layers = st.session_state.get("layers") or []
    shown = [r for r in results if r.key in active_layers]
    hints = move_hints(board, selected) if st.session_state.mode == PLAY_MODE else {}
    lastmove = (
        chess.Move.from_uci(line.moves[line.ply - 1]) if 0 < line.ply <= line.length else None
    )

    with board_slot:
        interactive_board(
            render_board(
                board,
                results=shown,
                orientation=orientation,
                size=board_size,
                extra_fill=hints,
                lastmove=lastmove,
            ),
            key=BOARD_KEY,
            orientation=orientation,
            selected=selected,
            size=board_size,
            on_square_change=on_square_click,
        )

    st.pills(
        "Camadas visuais",
        list(LAYER_LABELS),
        format_func=lambda key: LAYER_LABELS[key],
        selection_mode="multi",
        default=["pawn_structure", "weak_squares", "outposts"],
        key="layers",
        help="Escolha quais critérios pintam casas e setas no tabuleiro.",
    )

    with st.container(horizontal=True):
        st.badge("Vantagem / passado", color="green", icon=":material/check_circle:")
        st.badge("Fraqueza / isolado", color="red", icon=":material/warning:")
        st.badge("Atenção / travado", color="orange", icon=":material/lock:")
        st.badge("Tensão / referência", color="blue", icon=":material/adjust:")

with info_col:
    if problems:
        st.warning(
            "Posição incompleta — a análise fica pausada:\n\n"
            + "\n".join(f"- {problem}" for problem in problems)
        )

    turn_name = "Brancas" if board.turn == chess.WHITE else "Pretas"
    with st.container(horizontal=True):
        st.metric("Avaliação posicional", f"{score:+.2f}", delta=balance_label(score), border=True)
        st.metric("Lance de", turn_name, border=True)
        st.metric("Lance atual", f"{line.ply}/{line.length}", border=True)

    if board.is_checkmate():
        st.error("Xeque-mate.", icon=":material/flag:")
    elif board.is_stalemate():
        st.warning("Rei afogado — empate.", icon=":material/handshake:")
    elif board.is_check():
        st.info("Rei em xeque.", icon=":material/priority_high:")

    if line.length:
        with st.container(border=True):
            st.markdown("**Lances**")
            labels = line.move_labels()
            st.markdown(
                " ".join(
                    f"**:primary[{label}]**" if index + 1 == line.ply else label
                    for index, label in enumerate(labels)
                )
            )
            st.download_button(
                "Baixar PGN",
                line.to_pgn(),
                file_name="partida.pgn",
                mime="application/x-chess-pgn",
                icon=":material/download:",
            )

    st.code(board.fen(), language=None, wrap_lines=True)

    if results:
        plan_side_label = st.segmented_control(
            "Plano para", ["Brancas", "Pretas"], default=turn_name
        )
        plan_color = chess.BLACK if plan_side_label == "Pretas" else chess.WHITE

        with st.container(border=True):
            st.subheader("Plano de jogo sugerido (por prioridade)")
            st.markdown(f"**{summary_line(results, plan_color)}**")
            plan = build_plan(results, plan_color)
            if not plan:
                st.info("Nenhum plano identificado para esta posição.")
            for item in plan:
                st.markdown(
                    f"{STANCE_ICONS[item.stance]} **{item.priority}. {item.criterion}** "
                    f"({item.stance})  \n{item.action}"
                )

if results:
    st.divider()
    st.subheader("Critérios analisados")

    tabs = st.tabs([f"{index + 1}. {result.title}" for index, result in enumerate(results)])
    for tab, result in zip(tabs, results):
        with tab:
            edge = result.edge
            if edge is None:
                st.badge(result.verdict, color="gray", icon=":material/balance:")
            else:
                st.badge(
                    result.verdict,
                    color="green" if edge == chess.WHITE else "red",
                    icon=":material/insights:",
                )

            with st.container(horizontal=True):
                for metric in result.metrics:
                    st.metric(metric.label, metric.value, delta=metric.delta, border=True)

            detail_col, plan_col = st.columns(2)
            with detail_col:
                with st.container(border=True):
                    st.markdown("**Observações**")
                    for finding in result.findings:
                        st.markdown(f"- {finding}")
            with plan_col:
                with st.container(border=True):
                    st.markdown("**Planos**")
                    st.markdown("_Brancas_")
                    for plan_text in result.white_plans or ["—"]:
                        st.markdown(f"- {plan_text}")
                    st.markdown("_Pretas_")
                    for plan_text in result.black_plans or ["—"]:
                        st.markdown(f"- {plan_text}")

            with st.expander("Ver destaque deste critério no tabuleiro"):
                st.html(render_board(board, results=[result], orientation=orientation, size=340))

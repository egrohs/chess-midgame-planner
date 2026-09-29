"""Chess Midgame Planner — análise posicional e plano de jogo."""

from __future__ import annotations

import chess

import streamlit as st
from analysis import (
    analyze_position,
    balance_label,
    build_plan,
    overall_score,
    render_board,
    summary_line,
)

st.set_page_config(
    page_title="Chess Midgame Planner",
    page_icon=":material/strategy:",
    layout="wide",
)

STARTING_FEN = chess.STARTING_FEN

PRESETS: dict[str, str] = {
    "Posição inicial": STARTING_FEN,
    "Italiana — desenvolvimento": (
        "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 4 3"
    ),
    "Peão dama isolado (IQP)": "r1bq1rk1/pp2bppp/2n1pn2/8/2BP4/2N1BN2/PP3PPP/R2Q1RK1 b - - 1 10",
    "Centro fechado — Índia do Rei": (
        "r1bq1rk1/ppp1npbp/3p1np1/3Pp3/2P1P3/2N2N2/PP2BPPP/R1BQ1RK1 b - - 0 9"
    ),
    "Centro travado — Francesa do avanço": (
        "rnbqkbnr/pp3ppp/4p3/2ppP3/3P4/8/PPP2PPP/RNBQKBNR w KQkq - 0 4"
    ),
    "Peões dobrados — Ruy Lopez trocada": (
        "r1bqkbnr/1pp2ppp/p1p5/4p3/4P3/5N2/PPPP1PPP/RNBQ1RK1 b kq - 0 6"
    ),
    "Peão atrasado — Sveshnikov": (
        "r1bqkb1r/5ppp/p1np4/1p2p3/4P3/N1N5/PPP2PPP/R1BQKB1R b KQkq - 0 10"
    ),
    "Final com peão passado": "8/5ppp/8/3P4/8/6K1/5PPP/8 w - - 0 1",
}

LAYER_LABELS = {
    "material": "Material",
    "pawn_majority": "Maiorias",
    "development": "Desenvolvimento",
    "center": "Centro",
    "pawn_structure": "Estrutura",
}

STANCE_ICONS = {
    "explorar": ":material/trending_up:",
    "neutralizar": ":material/shield:",
    "equilibrado": ":material/balance:",
}


def load_board(fen: str) -> tuple[chess.Board | None, str | None]:
    try:
        return chess.Board(fen.strip()), None
    except ValueError as exc:
        return None, str(exc)


if "fen" not in st.session_state:
    st.session_state.fen = PRESETS["Italiana — desenvolvimento"]


def apply_preset() -> None:
    st.session_state.fen = PRESETS[st.session_state.preset]


st.title(":material/strategy: Chess Midgame Planner")
st.caption(
    "Analise uma posição por critérios posicionais de baixa complexidade "
    "e monte um plano de jogo com indicadores visuais."
)

with st.sidebar:
    st.subheader("Posição")
    st.selectbox(
        "Exemplos",
        list(PRESETS),
        index=1,
        key="preset",
        on_change=apply_preset,
    )
    st.text_area("FEN", key="fen", height=90)
    if st.button("Restaurar posição inicial", icon=":material/refresh:"):
        st.session_state.fen = STARTING_FEN
        st.rerun()

    st.subheader("Visualização")
    orientation_label = st.segmented_control(
        "Orientação do tabuleiro",
        ["Brancas", "Pretas"],
        default="Brancas",
    )
    board_size = st.slider("Tamanho do tabuleiro", 320, 720, 480, step=40)

board, error = load_board(st.session_state.fen)

if board is None:
    st.error(f"FEN inválido: {error}")
    st.stop()

results = analyze_position(board)
score = overall_score(results)
orientation = chess.BLACK if orientation_label == "Pretas" else chess.WHITE

board_col, info_col = st.columns([1.05, 1], gap="large")

with board_col:
    active_layers = st.pills(
        "Camadas visuais",
        list(LAYER_LABELS),
        format_func=lambda key: LAYER_LABELS[key],
        selection_mode="multi",
        default=["pawn_structure"],
        help="Escolha quais critérios pintam casas e setas no tabuleiro.",
    )
    shown = [r for r in results if r.key in (active_layers or [])]
    st.html(render_board(board, results=shown, orientation=orientation, size=board_size))

    legend = st.container(horizontal=True)
    with legend:
        st.badge("Vantagem / passado", color="green", icon=":material/check_circle:")
        st.badge("Fraqueza / isolado", color="red", icon=":material/warning:")
        st.badge("Atenção / travado", color="orange", icon=":material/lock:")
        st.badge("Tensão / referência", color="blue", icon=":material/adjust:")

with info_col:
    turn_name = "Brancas" if board.turn == chess.WHITE else "Pretas"
    with st.container(horizontal=True):
        st.metric("Avaliação posicional", f"{score:+.2f}", delta=balance_label(score), border=True)
        st.metric("Lance de", turn_name, border=True)

    plan_side_label = st.segmented_control(
        "Plano para",
        ["Brancas", "Pretas"],
        default=turn_name,
    )
    plan_color = chess.WHITE if plan_side_label == "Brancas" else chess.BLACK

    with st.container(border=True):
        st.subheader("Plano de jogo sugerido")
        st.markdown(f"**{summary_line(results, plan_color)}**")
        plan = build_plan(results, plan_color)
        if not plan:
            st.info("Nenhum plano identificado para esta posição.")
        for item in plan:
            st.markdown(
                f"{STANCE_ICONS[item.stance]} **{item.priority}. {item.criterion}** "
                f"({item.stance})  \n{item.action}"
            )

st.divider()
st.subheader("Critérios analisados")

tabs = st.tabs([f"{i + 1}. {r.title}" for i, r in enumerate(results)])
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

        preview = render_board(board, results=[result], orientation=orientation, size=340)
        with st.expander("Ver destaque deste critério no tabuleiro"):
            st.html(preview)

"""Testes de interface com AppTest (sem navegador)."""

from pathlib import Path

import chess
import pytest
from streamlit.testing.v1 import AppTest

from presets import PRESETS
from game import handle_setup_click

APP = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")


def run_app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def test_app_runs_without_exception():
    at = run_app()
    assert [tab.label for tab in at.tabs] == [
        "1. Segurança do rei",
        "2. Material bruto",
        "3. Atividade das peças",
        "4. Desenvolvimento / tempo",
        "5. Pior peça",
        "6. Estrutura básica de peões",
        "7. Centro aberto/fechado",
        "8. Casas fracas",
        "9. Outposts",
        "10. Maioria de peões",
        "11. Espaço",
    ]
    assert at.pills(key="layers").options == [
        "Segurança do rei",
        "Material",
        "Atividade",
        "Desenvolvimento",
        "Pior peça",
        "Estrutura",
        "Centro",
        "Casas fracas",
        "Outposts",
        "Maiorias",
        "Espaço",
    ]
    assert at.session_state.mode == "Mover peças"


@pytest.mark.parametrize("preset", list(PRESETS))
def test_every_preset_loads(preset):
    at = run_app()
    at.selectbox(key="preset").select(preset).run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state.line.board.is_valid()


def submit(at: AppTest, label: str) -> None:
    [button for button in at.button if button.label == label][0].click().run()


def test_invalid_fen_shows_error():
    at = run_app()
    at.text_area(key="fen_input").set_value("isto não é um fen")
    submit(at, "Aplicar FEN")
    assert not at.exception
    assert at.session_state.status[0] == "error"


def test_pgn_loads_moves():
    at = run_app()
    at.text_area(key="pgn_input").set_value("1. e4 e5 2. Nf3 Nc6 3. Bb5 a6")
    submit(at, "Aplicar PGN")
    assert not at.exception, [e.message for e in at.exception]
    line = at.session_state.line
    assert line.length == 6
    assert line.san_moves()[-1] == "a6"


def test_navigation_buttons_change_ply():
    at = run_app()
    at.text_area(key="pgn_input").set_value("1. e4 e5 2. Nf3")
    submit(at, "Aplicar PGN")
    assert at.session_state.line.ply == 3

    at.button(key="nav_first").click().run()
    assert at.session_state.line.ply == 0

    at.button(key="nav_next").click().run()
    assert at.session_state.line.ply == 1

    at.button(key="nav_last").click().run()
    assert at.session_state.line.ply == 3

    at.button(key="nav_prev").click().run()
    assert at.session_state.line.ply == 2

    at.button(key="nav_undo").click().run()
    assert at.session_state.line.length == 2


def test_ply_slider_navigates():
    at = run_app()
    at.text_area(key="pgn_input").set_value("1. e4 e5 2. Nf3 Nc6")
    submit(at, "Aplicar PGN")
    at.slider(key="ply_slider").set_value(1).run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state.line.ply == 1


def test_setup_mode_shows_palette_and_freezes_position():
    at = run_app()
    at.text_area(key="pgn_input").set_value("1. e4 e5")
    submit(at, "Aplicar PGN")

    at.segmented_control(key="mode").set_value("Montar posição").run()
    assert not at.exception, [e.message for e in at.exception]
    line = at.session_state.line
    assert line.moves == []
    assert line.board.piece_at(chess.E4) == chess.Piece(chess.PAWN, chess.WHITE)
    assert at.session_state.setup_piece == "P"
    assert at.segmented_control(key="setup_piece").proto.required


def test_setup_palette_remains_required_after_selecting_piece():
    at = run_app()
    at.segmented_control(key="mode").set_value("Montar posição").run()
    at.segmented_control(key="setup_piece").set_value("n").run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.segmented_control(key="setup_piece").proto.required
    assert at.session_state.setup_piece == "n"


def test_clear_board_pauses_analysis():
    at = run_app()
    at.segmented_control(key="mode").set_value("Montar posição").run()
    at.button(key="setup_clear").click().run()
    assert not at.exception, [e.message for e in at.exception]
    assert len(at.warning) >= 1
    assert len(at.tabs) == 0


def test_setup_turn_toggle():
    at = run_app()
    at.segmented_control(key="mode").set_value("Montar posição").run()
    at.segmented_control(key="setup_turn").set_value("Brancas").run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state.line.board.turn == chess.WHITE


def test_layers_pills_do_not_break_rendering():
    at = run_app()
    assert at.session_state.layers == ["pawn_structure", "weak_squares", "outposts"]
    at.pills(key="layers").set_value(["material", "center"]).run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state.layers == ["material", "center"]


def test_space_layer_can_be_selected():
    at = run_app()
    at.pills(key="layers").set_value(["space"]).run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state.layers == ["space"]
    assert at.tabs[-1].label == "11. Espaço"


def test_activity_layer_can_be_selected():
    at = run_app()
    at.pills(key="layers").set_value(["piece_activity"]).run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state.layers == ["piece_activity"]
    assert at.tabs[2].label == "3. Atividade das peças"


def test_king_safety_layer_can_be_selected():
    at = run_app()
    at.pills(key="layers").set_value(["king_safety"]).run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state.layers == ["king_safety"]
    assert at.tabs[0].label == "1. Segurança do rei"


def test_worst_piece_layer_can_be_selected():
    at = run_app()
    at.pills(key="layers").set_value(["worst_piece"]).run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state.layers == ["worst_piece"]
    assert at.tabs[4].label == "5. Pior peça"


def test_editing_board_updates_fen_field():
    """Editar o tabuleiro deve refletir o novo FEN no campo de texto."""
    at = run_app()
    at.segmented_control(key="mode").set_value("Montar posição").run()

    line = at.session_state.line
    at.session_state.line = handle_setup_click(line, chess.E4, "P")
    at.run()

    assert not at.exception, [e.message for e in at.exception]
    assert at.text_area(key="fen_input").value == at.session_state.line.board.fen()


def test_typed_fen_is_preserved_on_rerun():
    """Um FEN digitado pelo usuário não deve ser sobrescrito sem mudança de posição."""
    at = run_app()
    typed = "8/8/8/8/8/8/8/8 w - - 0 1"
    at.text_area(key="fen_input").set_value(typed).run()
    assert at.text_area(key="fen_input").value == typed


def test_loading_pgn_updates_fen_field():
    at = run_app()
    at.text_area(key="pgn_input").set_value("1. e4 e5 2. Nf3")
    submit(at, "Aplicar PGN")
    assert not at.exception, [e.message for e in at.exception]
    assert at.text_area(key="fen_input").value == at.session_state.line.board.fen()

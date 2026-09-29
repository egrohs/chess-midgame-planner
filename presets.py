"""Posições de exemplo, cada uma ilustrando um critério posicional."""

import chess

PRESETS: dict[str, str] = {
    "Posição inicial": chess.STARTING_FEN,
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
    "Final com peão passado": "6k1/5ppp/8/3P4/8/6K1/5PPP/8 w - - 0 1",
}

DEFAULT_PRESET = "Italiana — desenvolvimento"

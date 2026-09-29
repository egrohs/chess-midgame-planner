"""Critério 11 — Pior peça: compara oportunidades de melhoria por lado.

Combina a atividade já ponderada por casas úteis com desenvolvimento, apoio,
exposição a ataques e, para torres, acesso a colunas sem peões próprios.
Normaliza a atividade por tipo para não comparar a mobilidade bruta de um
cavalo com a de uma dama. Não calcula táticas nem lances futuros.
"""

from __future__ import annotations

from dataclasses import dataclass

import chess

from analysis.board_utils import MINOR_HOME_SQUARES, pawn_controlled_squares, relative_rank
from analysis.piece_activity import analyze_activity_for
from analysis.types import FILL, WARN, CriterionResult, Metric, clamp

EXPECTED_ACTIVITY = {
    chess.KNIGHT: 8.0,
    chess.BISHOP: 10.0,
    chess.ROOK: 12.0,
    chess.QUEEN: 16.0,
}
PIECE_NAMES = {
    chess.KNIGHT: "cavalo",
    chess.BISHOP: "bispo",
    chess.ROOK: "torre",
    chess.QUEEN: "dama",
}


@dataclass(frozen=True)
class PieceAssessment:
    square: chess.Square
    piece_type: chess.PieceType
    score: float
    reasons: tuple[str, ...]

    @property
    def label(self) -> str:
        return f"{PIECE_NAMES[self.piece_type]} em {chess.square_name(self.square)}"


def assess_pieces(board: chess.Board, color: chess.Color) -> list[PieceAssessment]:
    """Ordena peças menores e pesadas da mais limitada à mais bem colocada."""
    own_pawn_control = pawn_controlled_squares(board, color)
    enemy_pawn_control = pawn_controlled_squares(board, not color)
    assessments = []

    for activity in analyze_activity_for(board, color).pieces:
        source, piece_type = activity.square, activity.piece_type
        score = min(activity.quality / (2 * EXPECTED_ACTIVITY[piece_type]), 1.0)
        reasons = []

        if activity.destinations == 0:
            reasons.append("sem casas úteis acessíveis")
        elif activity.quality < EXPECTED_ACTIVITY[piece_type] * 0.35:
            reasons.append("poucas casas úteis acessíveis")
        if piece_type in (chess.KNIGHT, chess.BISHOP):
            if source in MINOR_HOME_SQUARES[color]:
                score -= 0.18
                reasons.append("ainda na casa inicial")
            if 2 <= chess.square_file(source) <= 5 and 2 <= chess.square_rank(source) <= 5:
                score += 0.1
            if relative_rank(source, color) >= 4 and source in own_pawn_control:
                score += 0.1
        elif piece_type == chess.ROOK:
            # Uma torre atrás dos peões na abertura não deve ser considerada
            # automaticamente pior que uma peça menor ainda não desenvolvida.
            score += 0.2
            if not board.pieces(chess.PAWN, color) & chess.BB_FILES[chess.square_file(source)]:
                score += 0.1
            else:
                reasons.append("coluna obstruída por peão próprio")
        else:
            score += 0.2

        if source in enemy_pawn_control:
            score -= 0.18
            reasons.append("exposta a peão adversário")
        elif board.is_attacked_by(not color, source) and not board.is_attacked_by(color, source):
            score -= 0.15
            reasons.append("atacada sem defesa")

        assessments.append(PieceAssessment(source, piece_type, clamp(score, 0.0, 1.0), tuple(reasons)))

    # Em caso de empate, melhorar uma peça menor é mais acionável na abertura.
    return sorted(
        assessments,
        key=lambda piece: (
            piece.score,
            piece.piece_type not in (chess.KNIGHT, chess.BISHOP),
            piece.square,
        ),
    )


def analyze_worst_piece(board: chess.Board) -> CriterionResult:
    white = assess_pieces(board, chess.WHITE)
    black = assess_pieces(board, chess.BLACK)
    white_worst = white[0] if white else None
    black_worst = black[0] if black else None
    score = (
        clamp((white_worst.score - black_worst.score) / 0.6)
        if white_worst is not None and black_worst is not None
        else 0.0
    )

    if abs(score) <= 0.05:
        verdict = "Os dois lados têm peças com necessidade semelhante de melhoria."
    elif score > 0:
        verdict = "A peça mais limitada das pretas precisa de mais atenção."
    else:
        verdict = "A peça mais limitada das brancas precisa de mais atenção."

    def describe(side: str, piece: PieceAssessment | None) -> str:
        if piece is None:
            return f"{side}: sem peças menores ou pesadas para comparar."
        reasons = ", ".join(piece.reasons) if piece.reasons else "menor índice relativo de atividade"
        return f"{side}: {piece.label} (índice {piece.score:.2f}) — {reasons}."

    def plan(piece: PieceAssessment | None) -> list[str]:
        if piece is None:
            return ["Sem peças menores ou pesadas; coordene rei e peões."]
        if "exposta a peão adversário" in piece.reasons or "atacada sem defesa" in piece.reasons:
            return [
                f"Proteja ou reposicione o {piece.label} antes de ampliar o ataque; "
                "confirme a segurança tática da manobra."
            ]
        if "sem casas úteis acessíveis" in piece.reasons:
            if piece.piece_type == chess.BISHOP:
                return [
                    f"Libere a diagonal do {piece.label} antes de desenvolvê-lo, "
                    "sem enfraquecer o próprio rei."
                ]
            return [
                f"Crie uma rota segura para o {piece.label} antes de tentar "
                "ativá-lo."
            ]
        if "ainda na casa inicial" in piece.reasons:
            return [
                f"Desenvolva o {piece.label} para uma casa útil e segura, "
                "preferencialmente com influência central."
            ]
        if "coluna obstruída por peão próprio" in piece.reasons:
            return [
                f"Melhore a {piece.label}: prepare uma coluna livre ou uma linha "
                "em que possa atuar sem perder proteção."
            ]
        return [
            f"Melhore o {piece.label} por uma manobra até casas úteis e seguras; "
            "não confunda o índice posicional com a melhor jogada tática."
        ]

    highlights = {}
    if white_worst is not None:
        highlights[white_worst.square] = FILL[WARN]
    if black_worst is not None:
        highlights[black_worst.square] = FILL[WARN]

    return CriterionResult(
        key="worst_piece",
        title="Pior peça",
        icon=":material/upgrade:",
        verdict=verdict,
        score=score,
        metrics=[
            Metric("Pior peça branca", white_worst.label if white_worst else "nenhuma"),
            Metric("Pior peça preta", black_worst.label if black_worst else "nenhuma"),
            Metric(
                "Índice relativo (B x P)",
                f"{white_worst.score:.2f} x {black_worst.score:.2f}"
                if white_worst and black_worst else "—",
            ),
        ],
        findings=[
            describe("Brancas", white_worst),
            describe("Pretas", black_worst),
            "Índices comparam mobilidade útil normalizada por tipo, desenvolvimento, "
            "apoio e exposição; não representam valor material nem análise tática.",
        ],
        white_plans=plan(white_worst),
        black_plans=plan(black_worst),
        highlights=highlights,
    )

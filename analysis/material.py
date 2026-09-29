"""Critério 1 — Material e desequilíbrios entre tipos de peças."""

from __future__ import annotations

import chess

from analysis.types import BAD, FILL, GOOD, CriterionResult, Metric, clamp

PIECE_VALUES: dict[chess.PieceType, float] = {
    chess.PAWN: 1.0,
    chess.KNIGHT: 3.0,
    chess.BISHOP: 3.25,
    chess.ROOK: 5.0,
    chess.QUEEN: 9.0,
}

PIECE_NAMES = {
    chess.PAWN: "peões",
    chess.KNIGHT: "cavalos",
    chess.BISHOP: "bispos",
    chess.ROOK: "torres",
    chess.QUEEN: "damas",
}


def count_material(board: chess.Board, color: chess.Color) -> dict[chess.PieceType, int]:
    return {ptype: len(board.pieces(ptype, color)) for ptype in PIECE_VALUES}


def material_value(counts: dict[chess.PieceType, int]) -> float:
    return sum(PIECE_VALUES[ptype] * n for ptype, n in counts.items())


def material_imbalances(
    white: dict[chess.PieceType, int],
    black: dict[chess.PieceType, int],
) -> list[tuple[str, chess.Color, str, str]]:
    """Compara excedentes opostos, sem contar a mesma peça em duas trocas."""
    surplus = {
        color: {ptype: max(0, mine[ptype] - theirs[ptype]) for ptype in PIECE_VALUES}
        for color, mine, theirs in (
            (chess.WHITE, white, black),
            (chess.BLACK, black, white),
        )
    }
    imbalances = []

    def take_minor(counts: dict[chess.PieceType, int]) -> chess.PieceType:
        for ptype in (chess.BISHOP, chess.KNIGHT):
            if counts[ptype]:
                counts[ptype] -= 1
                return ptype
        raise ValueError("Não há peça menor excedente para comparar.")

    for color in (chess.WHITE, chess.BLACK):
        mine, theirs = surplus[color], surplus[not color]
        while mine[chess.ROOK] >= 2 and theirs[chess.QUEEN]:
            mine[chess.ROOK] -= 2
            theirs[chess.QUEEN] -= 1
            imbalances.append((
                "duas torres contra dama", color,
                "Coordene as duas torres em linhas abertas e proteja-as de garfos da dama.",
                "Use a dama para criar ameaças múltiplas e evite trocá-la por apenas uma torre.",
            ))

    for color in (chess.WHITE, chess.BLACK):
        mine, theirs = surplus[color], surplus[not color]
        while mine[chess.QUEEN] and theirs[chess.ROOK] and theirs[chess.BISHOP] + theirs[chess.KNIGHT]:
            mine[chess.QUEEN] -= 1
            theirs[chess.ROOK] -= 1
            minor = take_minor(theirs)
            imbalances.append((
                f"dama contra torre e {PIECE_NAMES[minor][:-1]}", color,
                "Use a dama para criar ameaças em ambos os flancos; "
                "evite que a torre e a peça menor adversárias atuem em conjunto.",
                "Coordene a torre e a peça menor, proteja pontos fracos e limite os xeques da dama.",
            ))

    for color in (chess.WHITE, chess.BLACK):
        mine, theirs = surplus[color], surplus[not color]
        while mine[chess.ROOK] and theirs[chess.BISHOP] + theirs[chess.KNIGHT] >= 2:
            mine[chess.ROOK] -= 1
            minors = (take_minor(theirs), take_minor(theirs))
            names = {
                (chess.BISHOP, chess.BISHOP): "dois bispos",
                (chess.BISHOP, chess.KNIGHT): "bispo e cavalo",
                (chess.KNIGHT, chess.KNIGHT): "dois cavalos",
            }
            imbalances.append((
                f"torre contra {names[minors]}", color,
                "Ative a torre em colunas abertas e procure alvos em ambos os flancos; "
                "evite trocá-la por apenas uma peça menor sem compensação.",
                "Coordene as duas peças menores e restrinja as linhas da torre adversária.",
            ))

    for color in (chess.WHITE, chess.BLACK):
        mine, theirs = surplus[color], surplus[not color]
        while mine[chess.ROOK] and theirs[chess.BISHOP] + theirs[chess.KNIGHT]:
            mine[chess.ROOK] -= 1
            minor = take_minor(theirs)
            imbalances.append((
                f"torre contra {PIECE_NAMES[minor][:-1]} (qualidade)", color,
                "Use a torre em colunas abertas; conserve a vantagem de qualidade sem perder peões.",
                "Busque compensação com a peça menor em casas fortes e mantenha a posição ativa.",
            ))

    for color in (chess.WHITE, chess.BLACK):
        mine, theirs = surplus[color], surplus[not color]
        while mine[chess.BISHOP] and theirs[chess.KNIGHT]:
            mine[chess.BISHOP] -= 1
            theirs[chess.KNIGHT] -= 1
            imbalances.append((
                "bispo contra cavalo", color,
                "Procure diagonais abertas para o bispo e evite fixar todos os peões na sua cor.",
                "Busque casas fortes para o cavalo e restrinja as diagonais do bispo adversário.",
            ))
    return imbalances


def analyze_material(board: chess.Board) -> CriterionResult:
    white = count_material(board, chess.WHITE)
    black = count_material(board, chess.BLACK)
    white_value = material_value(white)
    black_value = material_value(black)
    diff = white_value - black_value

    findings: list[str] = []
    highlights: dict[chess.Square, str] = {}

    for ptype in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.PAWN):
        delta = white[ptype] - black[ptype]
        if delta == 0:
            continue
        leader = chess.WHITE if delta > 0 else chess.BLACK
        side = "Brancas" if leader else "Pretas"
        findings.append(f"{side} com {abs(delta)} {PIECE_NAMES[ptype]} a mais.")
        fill = FILL[GOOD] if leader == chess.WHITE else FILL[BAD]
        for square in board.pieces(ptype, leader):
            highlights[square] = fill

    white_pair = white[chess.BISHOP] >= 2
    black_pair = black[chess.BISHOP] >= 2
    if white_pair and not black_pair:
        findings.append("Brancas têm o par de bispos.")
    elif black_pair and not white_pair:
        findings.append("Pretas têm o par de bispos.")

    imbalances = material_imbalances(white, black)
    for name, color, _, _ in imbalances:
        side = "Brancas" if color == chess.WHITE else "Pretas"
        findings.append(f"{side} têm {name}.")
    pawn_delta = white[chess.PAWN] - black[chess.PAWN]
    if imbalances and pawn_delta:
        side = "brancas" if pawn_delta > 0 else "pretas"
        findings.append(
            f"Saldo adicional de peões: {abs(pawn_delta)} para as {side}; "
            "considere-o ao avaliar a troca de peças."
        )

    if abs(diff) < 0.25:
        verdict = "Material equilibrado em valor, mas com composição diferente." if imbalances else "Material equilibrado."
    elif abs(diff) < 1.5:
        side = "Brancas" if diff > 0 else "Pretas"
        verdict = f"Pequena vantagem material para as {side.lower()} ({abs(diff):+.2f})."
    elif abs(diff) < 3.0:
        side = "Brancas" if diff > 0 else "Pretas"
        verdict = f"{side} ganham um peão ou mais de material ({abs(diff):.2f})."
    else:
        side = "Brancas" if diff > 0 else "Pretas"
        verdict = f"Vantagem material decisiva das {side.lower()} ({abs(diff):.2f})."

    white_plans: list[str] = []
    black_plans: list[str] = []
    plans = {chess.WHITE: white_plans, chess.BLACK: black_plans}
    for _, color, own_plan, opposing_plan in imbalances:
        plans[color].append(own_plan)
        plans[not color].append(opposing_plan)
    if white_pair and not black_pair:
        white_plans.append("Abra a posição para valorizar o par de bispos.")
        black_plans.append("Restrinja as diagonais dos bispos adversários antes de abrir a posição.")
    elif black_pair and not white_pair:
        black_plans.append("Abra a posição para valorizar o par de bispos.")
        white_plans.append("Restrinja as diagonais dos bispos adversários antes de abrir a posição.")

    if diff >= 1.0:
        white_plans.append("Simplifique: troque peças (não peões) para converter o material extra.")
        black_plans.append("Evite trocas; busque compensação dinâmica e complique a posição.")
    elif diff <= -1.0:
        black_plans.append("Simplifique: troque peças (não peões) para converter o material extra.")
        white_plans.append("Evite trocas; busque compensação dinâmica e complique a posição.")
    elif not imbalances and white_pair == black_pair:
        white_plans.append("Sem desequilíbrio material: decida pelo critério posicional.")
        black_plans.append("Sem desequilíbrio material: decida pelo critério posicional.")

    metrics = [
        Metric("Material brancas", f"{white_value:.2f}"),
        Metric("Material pretas", f"{black_value:.2f}"),
        Metric("Saldo (brancas)", f"{diff:+.2f}", delta=f"{diff:+.2f}"),
        Metric("Trocas assimétricas", str(len(imbalances))),
    ]

    return CriterionResult(
        key="material",
        title="Material bruto",
        icon=":material/scale:",
        verdict=verdict,
        score=clamp(diff / 5.0),
        metrics=metrics,
        findings=findings or ["Nenhum desequilíbrio de peças."],
        white_plans=white_plans,
        black_plans=black_plans,
        highlights=highlights,
    )

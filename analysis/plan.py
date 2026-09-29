"""Consolidação dos critérios em um plano de jogo."""

from __future__ import annotations

from dataclasses import dataclass

import chess

from analysis.types import CriterionResult, color_name

# Peso de cada critério na avaliação consolidada.
WEIGHTS = {
    "material": 3.0,
    "pawn_majority": 1.0,
    "development": 1.5,
    "center": 1.0,
    "pawn_structure": 1.2,
    "weak_squares": 1.1,
    "outposts": 1.1,
    "space": 1.1,
    "piece_activity": 1.2,
    "king_safety": 1.5,
    "worst_piece": 1.0,
}


@dataclass
class PlanItem:
    priority: int
    criterion: str
    stance: str  # "explorar", "neutralizar" ou "equilibrado"
    action: str


def overall_score(results: list[CriterionResult]) -> float:
    """Média ponderada dos critérios, positiva a favor das brancas."""
    total_weight = sum(WEIGHTS.get(r.key, 1.0) for r in results)
    if not total_weight:
        return 0.0
    return sum(r.score * WEIGHTS.get(r.key, 1.0) for r in results) / total_weight


def balance_label(score: float) -> str:
    if abs(score) < 0.05:
        return "Posição equilibrada"
    side = "brancas" if score > 0 else "pretas"
    magnitude = abs(score)
    if magnitude < 0.15:
        return f"Leve iniciativa das {side}"
    if magnitude < 0.35:
        return f"Vantagem clara das {side}"
    return f"Vantagem grande das {side}"


def build_plan(
    results: list[CriterionResult], color: chess.Color, limit: int = 6
) -> list[PlanItem]:
    """Ordena os planos por relevância para a cor escolhida."""
    ranked = sorted(
        results,
        key=lambda r: (abs(r.score) * WEIGHTS.get(r.key, 1.0)),
        reverse=True,
    )

    items: list[PlanItem] = []
    for result in ranked:
        edge = result.edge
        if edge is None:
            stance = "equilibrado"
        elif edge == color:
            stance = "explorar"
        else:
            stance = "neutralizar"
        for action in result.plans_for(color):
            items.append(PlanItem(len(items) + 1, result.title, stance, action))

    # Remove duplicatas mantendo a ordem de prioridade.
    seen: set[str] = set()
    unique: list[PlanItem] = []
    for item in items:
        if item.action in seen:
            continue
        seen.add(item.action)
        unique.append(PlanItem(len(unique) + 1, item.criterion, item.stance, item.action))
        if len(unique) >= limit:
            break
    return unique


def summary_line(results: list[CriterionResult], color: chess.Color) -> str:
    score = overall_score(results)
    signed = score if color == chess.WHITE else -score
    if signed > 0.05:
        trend = "você está melhor — jogue para converter"
    elif signed < -0.05:
        trend = "você está pior — busque contra-jogo e simplificações favoráveis"
    else:
        trend = "posição equilibrada — melhore a pior peça e crie desequilíbrios"
    return f"{color_name(color)}: {trend}."

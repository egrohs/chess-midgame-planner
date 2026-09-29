"""Motor de análise posicional do Chess Midgame Planner."""

from analysis.board_render import move_hints, render_board
from analysis.center import analyze_center
from analysis.development import analyze_development
from analysis.material import analyze_material
from analysis.outposts import analyze_outposts
from analysis.pawn_majority import analyze_pawn_majority
from analysis.pawn_structure import analyze_pawn_structure
from analysis.plan import PlanItem, balance_label, build_plan, overall_score, summary_line
from analysis.space import analyze_space
from analysis.types import CriterionResult, Metric
from analysis.weak_squares import analyze_weak_squares

CRITERIA = (
    analyze_material,
    analyze_pawn_majority,
    analyze_development,
    analyze_center,
    analyze_pawn_structure,
    analyze_weak_squares,
    analyze_outposts,
    analyze_space,
)


def analyze_position(board) -> list[CriterionResult]:
    """Roda todos os critérios na ordem de complexidade crescente."""
    return [criterion(board) for criterion in CRITERIA]


__all__ = [
    "CRITERIA",
    "CriterionResult",
    "Metric",
    "PlanItem",
    "analyze_center",
    "analyze_development",
    "analyze_material",
    "analyze_outposts",
    "analyze_space",
    "analyze_pawn_majority",
    "analyze_pawn_structure",
    "analyze_position",
    "analyze_weak_squares",
    "balance_label",
    "build_plan",
    "move_hints",
    "overall_score",
    "render_board",
    "summary_line",
]

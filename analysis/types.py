"""Tipos compartilhados pelos critérios de análise."""

from __future__ import annotations

from dataclasses import dataclass, field

import chess

# Paleta usada tanto nos destaques do tabuleiro quanto nos badges da interface.
GOOD = "#2e7d32"
BAD = "#c62828"
WARN = "#ef6c00"
INFO = "#1565c0"
NEUTRAL = "#616161"

# Versões translúcidas para preencher casas do SVG sem esconder a peça.
FILL = {
    GOOD: "#2e7d3266",
    BAD: "#c6282866",
    WARN: "#ef6c0066",
    INFO: "#1565c066",
    NEUTRAL: "#61616166",
}


@dataclass(frozen=True)
class Metric:
    """Um número exibido como cartão na interface."""

    label: str
    value: str
    delta: str | None = None
    help: str | None = None


@dataclass
class Arrow:
    tail: chess.Square
    head: chess.Square
    color: str = INFO


@dataclass
class CriterionResult:
    """Resultado de um critério posicional."""

    key: str
    title: str
    icon: str
    verdict: str
    #: -1.0 (vantagem total das pretas) .. +1.0 (vantagem total das brancas)
    score: float = 0.0
    metrics: list[Metric] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    white_plans: list[str] = field(default_factory=list)
    black_plans: list[str] = field(default_factory=list)
    #: casa -> cor de preenchimento do SVG
    highlights: dict[chess.Square, str] = field(default_factory=dict)
    arrows: list[Arrow] = field(default_factory=list)

    @property
    def edge(self) -> chess.Color | None:
        """Cor favorecida pelo critério, ou ``None`` se equilibrado."""
        if self.score > 0.05:
            return chess.WHITE
        if self.score < -0.05:
            return chess.BLACK
        return None

    def plans_for(self, color: chess.Color) -> list[str]:
        return self.white_plans if color == chess.WHITE else self.black_plans


def clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def color_name(color: chess.Color) -> str:
    return "Brancas" if color == chess.WHITE else "Pretas"

from __future__ import annotations

from dataclasses import dataclass
from math import exp


@dataclass(frozen=True)
class LayoutConfig:
    CELL_SIZE_METERS: float = 1.0
    YAW_SNAP_DEG: float = 5.0
    DEFAULT_RECT_PERIMETER_SIZE: tuple[int, int] = (8, 8)
    DEFAULT_RECT_FILL_SIZE: tuple[int, int] = (6, 6)
    DEFAULT_CIRCLE_PERIMETER_RADIUS: int = 4
    DEFAULT_CIRCLE_FILL_RADIUS: int = 3
    DEFAULT_LINE_LENGTH: int = 7
    DEFAULT_LINE_SPLIT_FORWARD: int = 4
    DEFAULT_LINE_SPLIT_BACK: int = 3
    DEFAULT_CLUSTER_RADIUS: int = 2
    DEFAULT_FOLLOW_SPACING: int = 2
    DEFAULT_GATE_OPENING_SPAN: int = 2
    DEFAULT_CENTER_MAX_NUDGE: int = 3
    DEFAULT_NEAR_DECAY: float = 4.0
    DEFAULT_PERIMETER_STEP: int = 1
    SYMMETRY_EPSILON: float = 0.02

    def near_score(self, distance_cells: float) -> float:
        return exp(-distance_cells / self.DEFAULT_NEAR_DECAY)


DEFAULT_CONFIG = LayoutConfig()

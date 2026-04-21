from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Importance = Literal["primary", "secondary", "background"]
Mode = Literal[
    "scatter", "cluster", "line", "follow", "rect_perimeter", "rect_fill",
    "circle_perimeter", "circle_fill", "attach", "center"
]
Align = Literal["align_parallel", "align_perpendicular", "face_toward", "face_away"]


@dataclass
class LayoutObject:
    kind: str
    label: str
    count: int = 1
    roles: list[str] = field(default_factory=list)
    mode: str | None = None
    target: str | None = None
    inside: str | None = None
    outside: str | None = None
    around: str | None = None
    along: str | None = None
    near: str | None = None
    facing: str | None = None
    socket: str | None = None
    align: str | None = None
    traits: list[str] = field(default_factory=list)
    importance: str = "secondary"


@dataclass
class NormalizedObject(LayoutObject):
    host_ref: str | None = None
    align_ref: str | None = None
    target_kind: str | None = None
    zone_kind: str | None = None
    inferred_roles: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class EmitterIntent:
    kind: str
    label: str
    count: int
    emit: dict
    relations: dict = field(default_factory=dict)
    traits: list[str] = field(default_factory=list)
    importance: str = "secondary"

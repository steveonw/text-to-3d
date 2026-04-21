
from __future__ import annotations

from dataclasses import dataclass, field
from math import exp
from typing import Dict, List, Optional, Tuple

Point2 = Tuple[float, float]
Cell2 = Tuple[int, int]


@dataclass(frozen=True)
class TopologyVertex:
    host_id: str
    label: str
    x: int
    z: int


@dataclass
class TopologyCell:
    host_id: str
    side: str
    index: int
    x: int
    z: int
    nx: int
    nz: int
    thickness: float = 1.0
    blocked: bool = False
    role: str = "solid"  # solid | opening | shoulder

    @property
    def slot_id(self) -> str:
        return f"{self.host_id}:face:{self.side}:{self.index}"

    def center(self) -> Point2:
        return float(self.x), float(self.z)

    def face_point(self, face_side: str = "exterior") -> Point2:
        sign = 1.0 if face_side == "exterior" else -1.0
        return (
            self.x + self.nx * (self.thickness / 2.0) * sign,
            self.z + self.nz * (self.thickness / 2.0) * sign,
        )


@dataclass
class TopologySlot:
    slot_id: str
    family: str
    host_id: str
    side: str
    index: int
    x: float
    z: float
    yaw: int
    legal: bool = True
    blocked: bool = False
    tags: List[str] = field(default_factory=list)
    face_side: Optional[str] = None
    score_terms: Dict[str, float] = field(default_factory=dict)

    def point(self) -> Point2:
        return self.x, self.z


@dataclass
class GateEditResult:
    side: str
    opening_indices: List[int]
    shoulder_indices: List[int]


@dataclass
class RectTopology:
    host_id: str
    width: int
    height: int
    origin_x: int = 0
    origin_z: int = 0
    thickness: float = 1.0
    sides: Dict[str, List[TopologyCell]] = field(default_factory=dict)
    corners: Dict[str, TopologyVertex] = field(default_factory=dict)
    gate_edits: Dict[str, GateEditResult] = field(default_factory=dict)

    def all_side_cells(self) -> List[TopologyCell]:
        out: List[TopologyCell] = []
        for side in ("north", "east", "south", "west"):
            out.extend(self.sides.get(side, []))
        return out


CARDINAL_YAW = {
    "north": 0,
    "east": 1,
    "south": 2,
    "west": 3,
}


def midpoint_index(length: int) -> int:
    return (length // 2) if (length % 2 == 1) else ((length // 2) - 1)


def build_rect_topology(host_id: str, width: int, height: int, origin: Cell2 = (0, 0), thickness: float = 1.0) -> RectTopology:
    ox, oz = origin
    top = RectTopology(host_id=host_id, width=width, height=height, origin_x=ox, origin_z=oz, thickness=thickness)

    # corners are separate vertex nodes to avoid duplicate ownership
    top.corners = {
        "nw": TopologyVertex(host_id, "nw", ox, oz),
        "ne": TopologyVertex(host_id, "ne", ox + width - 1, oz),
        "se": TopologyVertex(host_id, "se", ox + width - 1, oz + height - 1),
        "sw": TopologyVertex(host_id, "sw", ox, oz + height - 1),
    }

    # half-open style with corners separated: side tracks own interior cells only
    north = [
        TopologyCell(host_id, "north", i, ox + 1 + i, oz, 0, -1, thickness=thickness)
        for i in range(max(0, width - 2))
    ]
    east = [
        TopologyCell(host_id, "east", i, ox + width - 1, oz + 1 + i, 1, 0, thickness=thickness)
        for i in range(max(0, height - 2))
    ]
    south = [
        TopologyCell(host_id, "south", i, ox + width - 2 - i, oz + height - 1, 0, 1, thickness=thickness)
        for i in range(max(0, width - 2))
    ]
    west = [
        TopologyCell(host_id, "west", i, ox, oz + height - 2 - i, -1, 0, thickness=thickness)
        for i in range(max(0, height - 2))
    ]

    top.sides = {"north": north, "east": east, "south": south, "west": west}
    return top


def apply_gate_edit(top: RectTopology, side: str, span: int, gate_label: str) -> GateEditResult:
    track = top.sides[side]
    if span <= 0:
        raise ValueError("gate span must be positive")
    if len(track) < span + 2:
        raise ValueError(f"gate span {span} too large for side '{side}' with {len(track)} interior cells")

    mid = midpoint_index(len(track))
    start = max(0, mid)
    if start + span > len(track):
        start = len(track) - span

    opening = list(range(start, start + span))
    left_sh = start - 1
    right_sh = start + span
    if left_sh < 0 or right_sh >= len(track):
        raise ValueError("gate edit requires shoulder cells on both sides")

    for idx in opening + [left_sh, right_sh]:
        cell = track[idx]
        if cell.role in {"opening", "shoulder"}:
            raise ValueError(f"gate edit overlaps existing opening/shoulder on {side}[{idx}]")

    for idx in opening:
        track[idx].blocked = True
        track[idx].role = "opening"
    for idx in [left_sh, right_sh]:
        track[idx].role = "shoulder"

    result = GateEditResult(side=side, opening_indices=opening, shoulder_indices=[left_sh, right_sh])
    top.gate_edits[gate_label] = result
    return result


def _opening_axis_for_gate(top: RectTopology, gate_label: str) -> Optional[float]:
    edit = top.gate_edits.get(gate_label)
    if not edit:
        return None
    track = top.sides[edit.side]
    pts = [track[i].center() for i in edit.opening_indices]
    if not pts:
        return None
    if edit.side in {"north", "south"}:
        return sum(x for x, _ in pts) / len(pts)
    return sum(z for _, z in pts) / len(pts)


def enumerate_slots(top: RectTopology, family: str, gate_label: Optional[str] = None, face_side: str = "exterior") -> List[TopologySlot]:
    slots: List[TopologySlot] = []
    if family == "opening":
        if gate_label and gate_label in top.gate_edits:
            edit = top.gate_edits[gate_label]
            track = top.sides[edit.side]
            pts = [track[i].center() for i in edit.opening_indices]
            x = sum(px for px, _ in pts) / len(pts)
            z = sum(pz for _, pz in pts) / len(pts)
            slots.append(TopologySlot(
                slot_id=f"{top.host_id}:opening:{edit.side}:0",
                family="opening",
                host_id=top.host_id,
                side=edit.side,
                index=0,
                x=x, z=z,
                yaw=CARDINAL_YAW[edit.side],
                blocked=False,
                tags=["opening"],
            ))
        return slots

    for side, track in top.sides.items():
        for cell in track:
            if cell.blocked and family != "edge":
                continue
            tags: List[str] = []
            if cell.role == "shoulder":
                tags.append("shoulder")
            if family == "face":
                x, z = cell.face_point(face_side=face_side)
                blocked = cell.blocked
            else:  # edge
                x, z = cell.center()
                blocked = cell.blocked
            slots.append(TopologySlot(
                slot_id=cell.slot_id.replace(":face:", f":{family}:"),
                family=family,
                host_id=cell.host_id,
                side=side,
                index=cell.index,
                x=x, z=z,
                yaw=CARDINAL_YAW[side],
                blocked=blocked,
                tags=tags,
                face_side=face_side if family == "face" else None,
            ))
    return slots


def score_near(slot: TopologySlot, ref: Optional[Point2]) -> float:
    if ref is None:
        return 0.0
    dx = slot.x - ref[0]
    dz = slot.z - ref[1]
    d = (dx * dx + dz * dz) ** 0.5
    return exp(-d / 4.0)


def rank_slots(
    slots: List[TopologySlot],
    near_ref: Optional[Point2] = None,
    gate_label: Optional[str] = None,
    top: Optional[RectTopology] = None,
    symmetry_eps: float = 0.02,
) -> List[TopologySlot]:
    axis = _opening_axis_for_gate(top, gate_label) if (top and gate_label) else None
    legal = [s for s in slots if s.legal and not s.blocked]
    for s in legal:
        s.score_terms["near"] = score_near(s, near_ref)
        s.score_terms["host_edit_bonus"] = 0.05 if "shoulder" in s.tags else 0.0
        s.score_terms["symmetry_pref"] = 0.0
        total = s.score_terms["near"] + s.score_terms["host_edit_bonus"]
        s.score_terms["total"] = total

    def sort_key(s: TopologySlot):
        return (
            0 if s.legal and not s.blocked else 1,
            -s.score_terms.get("host_edit_bonus", 0.0),
            -s.score_terms.get("near", 0.0),
            s.side,
            s.index,
            s.slot_id,
        )

    legal.sort(key=sort_key)

    if axis is not None and len(legal) >= 2:
        top_score = legal[0].score_terms["total"]
        tied = [s for s in legal if abs(s.score_terms["total"] - top_score) <= symmetry_eps]
        for s in tied:
            coord = s.x if s.side in {"north", "south"} else s.z
            s.score_terms["symmetry_pref"] = -abs(coord - axis)
        legal.sort(key=lambda s: (
            0 if s.legal and not s.blocked else 1,
            -s.score_terms.get("host_edit_bonus", 0.0),
            -s.score_terms.get("near", 0.0),
            -s.score_terms.get("symmetry_pref", 0.0),
            s.side,
            s.index,
            s.slot_id,
        ))
    return legal


def debug_ascii(top: RectTopology, placements: Optional[List[Tuple[str, Point2]]] = None) -> str:
    placements = placements or []
    marks = {(round(x), round(z)): ch for ch, (x, z) in placements}
    minx = top.origin_x
    maxx = top.origin_x + top.width - 1
    minz = top.origin_z
    maxz = top.origin_z + top.height - 1
    lines: List[str] = []
    for z in range(minz, maxz + 1):
        row = []
        for x in range(minx, maxx + 1):
            if (x, z) in marks:
                row.append(marks[(x, z)])
                continue
            ch = "~"
            for v in top.corners.values():
                if v.x == x and v.z == z:
                    ch = "C"
                    break
            else:
                for cell in top.all_side_cells():
                    if cell.x == x and cell.z == z:
                        if cell.role == "opening":
                            ch = "."
                        elif cell.role == "shoulder":
                            ch = "|"
                        else:
                            ch = "#"
                        break
            row.append(ch)
        lines.append(" ".join(row))
    return "\n".join(lines)


def dump_topology_svg(top: RectTopology, filename: str, slots: Optional[List[TopologySlot]] = None) -> None:
    slots = slots or []
    scale = 20
    pad = 20
    width = (top.width + 2) * scale
    height = (top.height + 2) * scale

    def sx(x: float) -> float:
        return pad + (x - top.origin_x + 1) * scale

    def sy(z: float) -> float:
        return pad + (z - top.origin_z + 1) * scale

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">']
    # side cells
    for cell in top.all_side_cells():
        color = "#000000"
        if cell.role == "opening":
            color = "#ff0000"
        elif cell.role == "shoulder":
            color = "#aa5500"
        parts.append(f'<circle cx="{sx(cell.x)}" cy="{sy(cell.z)}" r="4" fill="{color}" />')
    # corners
    for v in top.corners.values():
        parts.append(f'<rect x="{sx(v.x)-3}" y="{sy(v.z)-3}" width="6" height="6" fill="#4444aa" />')
    # slots
    for slot in slots:
        parts.append(f'<circle cx="{sx(slot.x)}" cy="{sy(slot.z)}" r="2" fill="#0088ff" />')
    parts.append("</svg>")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.dropgrid.topology import (
    build_rect_topology,
    apply_gate_edit,
    enumerate_slots,
    rank_slots,
    debug_ascii,
)


def test_rect_topology_has_separate_corners_and_half_open_sides():
    top = build_rect_topology("yard", 8, 8)
    assert set(top.corners.keys()) == {"nw", "ne", "se", "sw"}
    assert len(top.sides["north"]) == 6
    assert len(top.sides["east"]) == 6
    assert len(top.sides["south"]) == 6
    assert len(top.sides["west"]) == 6
    side_points = {(c.x, c.z) for c in top.all_side_cells()}
    corner_points = {(v.x, v.z) for v in top.corners.values()}
    assert side_points.isdisjoint(corner_points)


def test_apply_gate_edit_marks_opening_and_shoulders():
    top = build_rect_topology("yard", 8, 8)
    edit = apply_gate_edit(top, "south", 2, "front_gate")
    assert edit.side == "south"
    assert len(edit.opening_indices) == 2
    assert len(edit.shoulder_indices) == 2
    south = top.sides["south"]
    for idx in edit.opening_indices:
        assert south[idx].role == "opening"
        assert south[idx].blocked is True
    for idx in edit.shoulder_indices:
        assert south[idx].role == "shoulder"


def test_enumerate_opening_slot_uses_gap_midpoint():
    top = build_rect_topology("yard", 8, 8)
    apply_gate_edit(top, "south", 2, "front_gate")
    slots = enumerate_slots(top, "opening", gate_label="front_gate")
    assert len(slots) == 1
    slot = slots[0]
    assert slot.family == "opening"
    assert slot.side == "south"
    # midpoint of two opening cells on south side should sit on the south edge
    assert slot.z == 7.0


def test_face_slots_offset_from_host_centerline_by_thickness():
    top = build_rect_topology("yard", 8, 8, thickness=2.0)
    north_face = [s for s in enumerate_slots(top, "face") if s.side == "north"][0]
    north_edge = [s for s in enumerate_slots(top, "edge") if s.side == "north"][0]
    assert north_edge.z == 0.0
    assert north_face.z == -1.0  # thickness / 2 on north normal


def test_rank_slots_prefers_near_then_symmetry():
    top = build_rect_topology("yard", 8, 8)
    apply_gate_edit(top, "south", 2, "front_gate")
    slots = enumerate_slots(top, "face")
    ranked = rank_slots(slots, near_ref=(3.5, 7.0), gate_label="front_gate", top=top)
    top_two = ranked[:2]
    assert all("shoulder" in s.tags for s in top_two)
    assert {s.side for s in top_two} == {"south"}


def test_debug_ascii_shows_openings_shoulders_and_corners():
    top = build_rect_topology("yard", 8, 8)
    apply_gate_edit(top, "south", 2, "front_gate")
    art = debug_ascii(top)
    assert "C" in art
    assert "|" in art
    assert "." in art

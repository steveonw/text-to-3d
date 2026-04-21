from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from scripts.dropgrid.topology_candidate.layout_normalizer import parse_layout_dsl, normalize_objects, LayoutSpecError
from scripts.dropgrid.topology_candidate.layout_compiler import compile_layout_dsl


def test_attach_defaults_count_and_mode():
    text = """
object torch
  label wall_torch
  target wall_1
  socket face

object wall
  label wall_1
"""
    objs = parse_layout_dsl(text)
    norm = normalize_objects(objs)
    torch = next(o for o in norm if o.label == "wall_torch")
    assert torch.count == 1
    assert torch.mode == "attach"
    assert torch.importance == "secondary"


def test_synonym_normalization():
    text = """
object palisade
  label yard_wall
"""
    norm = normalize_objects(parse_layout_dsl(text))
    obj = norm[0]
    assert obj.kind == "fence"
    assert "barrier" in obj.roles
    assert obj.mode == "line"


def test_illegal_socket_host():
    text = """
object tree
  label tree_1

object torch
  label tree_torch
  target tree_1
  socket face
"""
    with pytest.raises(LayoutSpecError) as exc:
        normalize_objects(parse_layout_dsl(text))
    assert "illegal" in exc.value.reason


def test_inside_fill_of_one_promotes_center():
    text = """
object fence
  label yard_edge
  mode rect_perimeter

object fountain
  label yard_fountain
  inside yard_edge
"""
    norm = normalize_objects(parse_layout_dsl(text))
    fountain = next(o for o in norm if o.label == "yard_fountain")
    assert fountain.mode == "center"


def test_align_reference_priority_near_beats_inside():
    text = """
object fence
  label market_fence
  mode rect_perimeter

object gate
  label market_entry
  roles gate_opening gate_frame
  target market_fence
  socket opening
  facing east

object stall
  label cloth_stall
  inside market_fence
  near market_entry
  align face_toward
"""
    norm = normalize_objects(parse_layout_dsl(text))
    stall = next(o for o in norm if o.label == "cloth_stall")
    assert stall.align_ref == "market_entry"


def test_gate_opening_compiles_special_op():
    text = """
object fence
  label yard_fence
  mode rect_perimeter

object gate
  label south_gate
  roles gate_opening gate_frame
  target yard_fence
  socket opening
  facing south
  importance primary
"""
    intents = compile_layout_dsl(text)
    gate = next(i for i in intents if i.label == "south_gate")
    assert gate.emit["placement_mode"] == "attach"
    assert gate.relations["special_op"]["type"] == "gate_opening"
    assert gate.relations["special_op"]["side"] == "south"

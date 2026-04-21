from __future__ import annotations
from .parser import parse_object_scene
from .planner import normalize_spec
from .solver import solve_compiled

def solve_object_scene(text: str, seed: int = 42, debug: bool = False):
    raw_spec = parse_object_scene(text)
    spec = normalize_spec(raw_spec)
    return solve_compiled(spec, seed=seed, debug=debug)

def solve_scene(text: str, seed: int = 42, debug: bool = False):
    return solve_object_scene(text, seed=seed, debug=debug)

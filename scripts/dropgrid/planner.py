from __future__ import annotations
from .footprints import footprint_span

def _ma_radius(spec: dict) -> int:
    ma = spec.get("ma")
    if isinstance(ma, dict):
        return int(ma.get("radius") or 0)
    return int(ma or 0)

def _ma_mode(spec: dict) -> str | None:
    ma = spec.get("ma")
    if isinstance(ma, dict):
        return ma.get("mode", "hard")
    return "hard" if ma else None

def _motif_clearance(piece_type: str, spread: float) -> int:
    base = 1
    span = footprint_span(piece_type)
    if span >= 2:
        base = span
    if spread and spread > 0:
        base += 1
    return base

def normalize_spec(spec: dict) -> dict:
    """Planner pass: repair obvious intent conflicts while recording warnings.

    Rule:
    - Planner may repair.
    - Solver stays strict.
    """
    out = {
        "anchor": dict(spec.get("anchor") or {}),
        "ma": spec.get("ma"),
        "objects": [],
        "warnings": [],
    }
    mode = _ma_mode(spec)
    ma_r = _ma_radius(spec)
    for obj in spec.get("objects", []):
        fixed = dict(obj)
        if mode == "hard" and "radius" in fixed:
            req_r = int(fixed.get("radius", 0))
            clearance = _motif_clearance(fixed.get("type", ""), fixed.get("spread", 0))
            min_safe = ma_r + clearance
            if req_r < min_safe:
                fixed["requested_radius"] = req_r
                fixed["radius"] = min_safe + 1
                label = fixed.get("label", fixed.get("type", "object"))
                out["warnings"].append(
                    f"{label}: requested radius {req_r} overlapped hard MA radius {ma_r}; adjusted to {fixed['radius']}"
                )
        out["objects"].append(fixed)
    return out

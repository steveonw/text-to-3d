"""
geometry_receiver.py — Validate and normalise LLM-authored geometry packets.

A geometry packet describes the visual appearance of one placed piece as a
list of Three.js-style primitives in the piece's local coordinate space.
The scaffold (task 4) consumes these packets to assemble the final HTML.

See scripts/authoring/schema.md for the full format documentation.

Public API
----------
    validate_primitive(prim)   → normalised prim dict, raises GeometryError
    validate_packet(packet)    → normalised packet dict, raises GeometryError
    receive_packet(packet)     → alias for validate_packet
    receive_all(packets)       → {piece_id: packet}, raises GeometryError on first bad one
    GeometryError              → raised for any schema violation
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Union

# ── Shape catalogue ────────────────────────────────────────────────────────────

SUPPORTED_SHAPES = {"box", "cylinder", "cone", "sphere", "plane"}

# Number of dimension values each shape requires
_SHAPE_DIM_COUNT = {
    "box":      3,  # [width, height, depth]
    "cylinder": 3,  # [radius_top, radius_bottom, height]
    "cone":     2,  # [radius, height]
    "sphere":   1,  # [radius]
    "plane":    2,  # [width, height]
}

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


# ── Error type ─────────────────────────────────────────────────────────────────

class GeometryError(ValueError):
    """Raised when a geometry packet fails schema validation."""


# ── Helpers ────────────────────────────────────────────────────────────────────

def _require(condition: bool, msg: str) -> None:
    if not condition:
        raise GeometryError(msg)


def _valid_color(v: Any) -> str:
    _require(
        isinstance(v, str) and bool(_HEX_RE.match(v)),
        f"color must be a 6-digit hex string like '#a1b2c3', got {v!r}",
    )
    return v.lower()


def _valid_vec3(v: Any, name: str) -> List[float]:
    _require(
        isinstance(v, (list, tuple))
        and len(v) == 3
        and all(isinstance(x, (int, float)) for x in v),
        f"{name} must be a list of 3 numbers, got {v!r}",
    )
    return [float(x) for x in v]


# ── Material validation ────────────────────────────────────────────────────────

def _validate_material(mat: Any) -> dict:
    _require(isinstance(mat, dict), f"material must be a dict, got {type(mat).__name__!r}")
    _require("color" in mat, "material must have a 'color' key")

    out: dict = {"color": _valid_color(mat["color"])}

    for key in ("roughness", "metalness"):
        if key in mat:
            val = mat[key]
            _require(
                isinstance(val, (int, float)) and 0.0 <= float(val) <= 1.0,
                f"material.{key} must be a float in [0, 1], got {val!r}",
            )
            out[key] = float(val)
        else:
            out[key] = 0.85 if key == "roughness" else 0.05

    if "emissive" in mat:
        out["emissive"] = _valid_color(mat["emissive"])
        intensity = mat.get("emissive_intensity", 0.5)
        _require(
            isinstance(intensity, (int, float)) and float(intensity) >= 0,
            f"material.emissive_intensity must be a non-negative number, got {intensity!r}",
        )
        out["emissive_intensity"] = float(intensity)

    return out


# ── Primitive validation ───────────────────────────────────────────────────────

def validate_primitive(prim: Any) -> dict:
    """Validate and normalise a single primitive dict.

    Raises GeometryError on any violation.
    Returns a clean, normalised dict ready for the scaffold.
    """
    _require(isinstance(prim, dict), f"primitive must be a dict, got {type(prim).__name__!r}")

    shape = prim.get("shape")
    _require(
        shape in SUPPORTED_SHAPES,
        f"shape must be one of {sorted(SUPPORTED_SHAPES)}, got {shape!r}",
    )

    dims = prim.get("dimensions")
    expected = _SHAPE_DIM_COUNT[shape]
    _require(
        isinstance(dims, (list, tuple))
        and len(dims) == expected
        and all(isinstance(d, (int, float)) for d in dims),
        f"{shape} requires exactly {expected} numeric dimension(s), got {dims!r}",
    )
    _require(
        all(float(d) > 0 for d in dims),
        f"all dimensions must be positive, got {list(dims)!r}",
    )

    pos = _valid_vec3(prim.get("position", [0.0, 0.0, 0.0]), "position")
    rot = _valid_vec3(prim.get("rotation", [0.0, 0.0, 0.0]), "rotation")

    mat = prim.get("material")
    _require(mat is not None, "primitive must have a 'material' key")
    mat = _validate_material(mat)

    return {
        "shape": shape,
        "dimensions": [float(d) for d in dims],
        "position": pos,
        "rotation": rot,
        "material": mat,
    }


# ── Packet validation ──────────────────────────────────────────────────────────

def validate_packet(packet: Any) -> dict:
    """Validate and normalise a full geometry packet.

    Raises GeometryError on any violation.
    Returns a clean dict: {"piece_id": int, "primitives": [...]}.
    """
    _require(isinstance(packet, dict), f"packet must be a dict, got {type(packet).__name__!r}")

    pid = packet.get("piece_id")
    _require(
        isinstance(pid, int) and pid >= 0,
        f"piece_id must be a non-negative int, got {pid!r}",
    )

    prims_raw = packet.get("primitives")
    _require(
        isinstance(prims_raw, list) and len(prims_raw) > 0,
        "primitives must be a non-empty list",
    )

    validated_prims = []
    for i, prim in enumerate(prims_raw):
        try:
            validated_prims.append(validate_primitive(prim))
        except GeometryError as exc:
            raise GeometryError(f"primitives[{i}]: {exc}") from exc

    return {"piece_id": pid, "primitives": validated_prims}


# ── Public API ─────────────────────────────────────────────────────────────────

def receive_packet(packet: Any) -> dict:
    """Validate a single geometry packet and return the normalised version.

    Raises GeometryError if invalid.
    """
    return validate_packet(packet)


def receive_all(packets: Union[List[Any], Dict[Any, Any]]) -> Dict[int, dict]:
    """Validate a collection of geometry packets.

    Accepts either a list of packet dicts or a dict keyed by piece_id.
    Returns {piece_id: normalised_packet}.
    Raises GeometryError on the first invalid packet.
    """
    _require(
        isinstance(packets, (list, dict)),
        f"packets must be a list or dict, got {type(packets).__name__!r}",
    )
    items: List[Any] = list(packets.values()) if isinstance(packets, dict) else packets
    result: Dict[int, dict] = {}
    for item in items:
        validated = validate_packet(item)
        result[validated["piece_id"]] = validated
    return result

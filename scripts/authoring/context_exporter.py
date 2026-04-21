"""
context_exporter.py — Per-piece context packets for geometry authoring.

Takes a solved SceneResult and emits a context packet for each piece describing
its nearest neighbors, spatial role (edge / interior / corner), path proximity,
and the direction "outward" from the scene center.

These packets are consumed by the geometry authoring protocol so that each
piece can be authored in context: a tree at the path edge looks different from
one deep in the forest; the third fence post in a corner reads different from
one mid-wall.

Public API
----------
    export_piece_context(piece, scene_result, neighbors=5) -> dict
    export_all_contexts(scene_result, neighbors=5) -> dict[int, dict]
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from dropgrid.models import Piece, SceneResult

# ── Constants ──────────────────────────────────────────────────────────────────

_COMPASS_8 = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
_ROT_TO_FACING = {0: "N", 1: "E", 2: "S", 3: "W"}

# Piece types / families that count as "path" for proximity checks
_PATH_FAMILIES = {"path"}
_PATH_TYPES = {"road"}

# Anchor/host pieces are always interior — they are the focal points of scenes
_ALWAYS_INTERIOR_FAMILIES = {"anchor", "host"}

# Radius (grid cells) used when classifying edge vs. interior
_EDGE_CHECK_RADIUS = 4.5

# Distance threshold for "near path"
_NEAR_PATH_THRESHOLD = 2.5


# ── Low-level geometry helpers ─────────────────────────────────────────────────

def _dist(p1: Piece, p2: Piece) -> float:
    return math.sqrt((p1.gx - p2.gx) ** 2 + (p1.gz - p2.gz) ** 2)


def _compass8(dx: float, dz: float) -> str:
    """Grid-space delta → 8-point compass label. z+ is south."""
    angle = math.degrees(math.atan2(dx, -dz)) % 360
    return _COMPASS_8[round(angle / 45) % 8]


def _scene_center(pieces: List[Piece]) -> Tuple[float, float]:
    if not pieces:
        return 0.0, 0.0
    return (
        sum(p.gx for p in pieces) / len(pieces),
        sum(p.gz for p in pieces) / len(pieces),
    )


def _is_path_piece(p: Piece) -> bool:
    return p.family in _PATH_FAMILIES or p.type in _PATH_TYPES


# ── Context components ─────────────────────────────────────────────────────────

def _nearest_neighbors(piece: Piece, all_pieces: List[Piece], n: int) -> List[dict]:
    others = sorted(
        (p for p in all_pieces if p.id != piece.id),
        key=lambda p: _dist(piece, p),
    )
    result = []
    for other in others[:n]:
        d = _dist(piece, other)
        result.append({
            "id": other.id,
            "type": other.type,
            "label": other.label,
            "family": other.family,
            "distance": round(d, 2),
            "direction": _compass8(other.gx - piece.gx, other.gz - piece.gz),
        })
    return result


def _near_path_info(
    piece: Piece, all_pieces: List[Piece]
) -> Tuple[bool, Optional[str]]:
    """Return (near_path, direction_to_nearest_path_piece)."""
    closest_d = float("inf")
    closest_dir: Optional[str] = None
    for other in all_pieces:
        if other.id == piece.id or not _is_path_piece(other):
            continue
        d = _dist(piece, other)
        if d <= _NEAR_PATH_THRESHOLD and d < closest_d:
            closest_d = d
            closest_dir = _compass8(other.gx - piece.gx, other.gz - piece.gz)
    return closest_dir is not None, closest_dir


def _sector_occupancy(piece: Piece, all_pieces: List[Piece], radius: float) -> List[bool]:
    """8 booleans, one per 45° sector, True if any neighbor falls in that sector."""
    occupied = [False] * 8
    for other in all_pieces:
        if other.id == piece.id:
            continue
        dx = other.gx - piece.gx
        dz = other.gz - piece.gz
        if math.sqrt(dx * dx + dz * dz) > radius:
            continue
        angle = math.degrees(math.atan2(dx, -dz)) % 360
        occupied[round(angle / 45) % 8] = True
    return occupied


def _on_cluster_edge(piece: Piece, all_pieces: List[Piece]) -> bool:
    """True if the piece sits on the periphery of the scene's piece cluster.

    Two-stage test:
    1. Pieces within the inner 35% of the scene's radial extent are always
       interior (handles anchors/altars at the center of a ring layout).
    2. For outer pieces, check for an unoccupied 180° half-space within the
       edge-check radius by sliding a 4-sector window around 8 sectors.
    """
    if len(all_pieces) <= 4:
        return True

    # Anchor and host pieces are definitionally interior (scene focal points)
    if piece.family in _ALWAYS_INTERIOR_FAMILIES:
        return False

    cx, cz = _scene_center(all_pieces)
    max_dist = max(
        math.sqrt((p.gx - cx) ** 2 + (p.gz - cz) ** 2) for p in all_pieces
    )
    if max_dist < 1.0:
        return False

    piece_dist = math.sqrt((piece.gx - cx) ** 2 + (piece.gz - cz) ** 2)
    if piece_dist < max_dist * 0.35:
        return False

    occ = _sector_occupancy(piece, all_pieces, _EDGE_CHECK_RADIUS)
    doubled = occ * 2
    return any(not any(doubled[s : s + 4]) for s in range(8))


def _in_corner(piece: Piece, all_pieces: List[Piece]) -> bool:
    """True if two or more consecutive sectors are empty within a tighter radius.

    A piece is 'in a corner' when it sits at a bend: neighbors cluster in
    fewer than 6 of the 8 sectors AND at least two adjacent sectors are empty.
    """
    if len(all_pieces) <= 4:
        return False
    occ = _sector_occupancy(piece, all_pieces, _EDGE_CHECK_RADIUS * 0.8)
    doubled = occ * 2
    return any(not doubled[s] and not doubled[s + 1] for s in range(8))


def _outward_direction(piece: Piece, cx: float, cz: float) -> str:
    """Compass direction from the scene center toward this piece."""
    dx = piece.gx - cx
    dz = piece.gz - cz
    if abs(dx) < 0.5 and abs(dz) < 0.5:
        return "center"
    return _compass8(dx, dz)


# ── Public API ─────────────────────────────────────────────────────────────────

def export_piece_context(
    piece: Piece, scene_result: SceneResult, neighbors: int = 5
) -> dict:
    """Return a context packet for a single piece.

    Keys
    ----
    self            — identity and position of the piece itself
    neighbors       — up to `neighbors` nearest pieces, sorted by distance
    near_path       — True if a road/path piece is within 2.5 cells
    path_direction  — compass direction toward the nearest path piece, or None
    on_cluster_edge — True if an empty 180° half-space exists nearby
    interior        — opposite of on_cluster_edge
    in_corner       — True if two adjacent sectors are empty (bend / corner)
    outward_direction — compass direction from scene center toward this piece
    scene_center    — mean position of all pieces (x, z)
    """
    all_pieces = scene_result.pieces
    cx, cz = _scene_center(all_pieces)
    near_path, path_dir = _near_path_info(piece, all_pieces)
    edge = _on_cluster_edge(piece, all_pieces)

    return {
        "self": {
            "id": piece.id,
            "type": piece.type,
            "label": piece.label,
            "group": piece.group,
            "family": piece.family,
            "position": {"x": piece.gx, "z": piece.gz},
            "rot": piece.rot,
            "facing": _ROT_TO_FACING.get(piece.rot % 4, "N"),
        },
        "neighbors": _nearest_neighbors(piece, all_pieces, neighbors),
        "near_path": near_path,
        "path_direction": path_dir,
        "on_cluster_edge": edge,
        "interior": not edge,
        "in_corner": _in_corner(piece, all_pieces) if edge else False,
        "outward_direction": _outward_direction(piece, cx, cz),
        "scene_center": {"x": round(cx, 1), "z": round(cz, 1)},
    }


def export_all_contexts(
    scene_result: SceneResult, neighbors: int = 5
) -> Dict[int, dict]:
    """Return a context packet for every piece, keyed by piece id."""
    return {
        piece.id: export_piece_context(piece, scene_result, neighbors)
        for piece in scene_result.pieces
    }

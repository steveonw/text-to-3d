from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

Cell3 = Tuple[int, int, int]

@dataclass
class Piece:
    id: int
    type: str
    label: str
    gx: int
    gy: int
    gz: int
    rot: int = 0
    cells: List[Cell3] = field(default_factory=list)
    group: str = ""
    family: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SceneResult:
    pieces: List[Piece]
    meta: Dict[str, Any]
    trace: List[Dict[str, Any]]

    def to_ascii(
        self,
        include_legend: bool = False,
        show_axes: bool = True,
        include_warnings: bool = True,
        symbol_overrides: Dict[str, str] | None = None,
        show_borders: bool = True,
        show_heights: bool = False,
    ):
        from .exporters import result_to_ascii
        return result_to_ascii(
            self,
            include_legend=include_legend,
            show_axes=show_axes,
            include_warnings=include_warnings,
            symbol_overrides=symbol_overrides,
            show_borders=show_borders,
            show_heights=show_heights,
        )

    def to_layout(self, fmt: str = "parts") -> Dict[str, Any]:
        """Convert pieces to a verifier-compatible layout dict.

        Returns a dict shaped for the v4 verifiers:
            {
              "room": {"width": W, "depth": D, "height": H},
              "parts" or "items": [ {name, x, z, y?, w, d, h}, ... ]
            }

        fmt='parts'  → braille_view format.   x, z are centered on the room.
        fmt='items'  → layout_compare/spatial_validate format.  x, z are
                       corner-positioned, y is the part's vertical center.

        Per-piece footprint (w × d) is taken from `p.cells` when the piece
        occupies multiple cells (e.g. fences / walls); otherwise a per-type
        default is used so single-cell pieces render at sensible sizes.

        h (height) defaults to 1.0 — override on the returned parts if a
        verifier needs accurate elevation.
        """
        if fmt not in ("parts", "items"):
            raise ValueError(f"fmt must be 'parts' or 'items', got {fmt!r}")

        # Per-type default footprints (cells units = grid units)
        default_bbox = {
            "campfire":  (1.2, 1.2, 1.0),
            "fountain":  (1.4, 1.4, 1.5),
            "altar":     (1.4, 1.4, 1.0),
            "tree":      (1.5, 1.5, 3.5),
            "lantern":   (0.6, 0.6, 1.5),
            "fence":     (1.0, 1.0, 1.4),
            "wall":      (1.0, 1.0, 2.5),
            "log":       (1.1, 0.4, 0.4),
            "rubble":    (0.7, 0.7, 0.7),
            "road":      (1.0, 1.0, 0.1),
            "gate":      (1.0, 0.4, 2.0),
        }

        # Compute room bounds from piece extent + small padding
        if not self.pieces:
            room = {"width": 4.0, "depth": 4.0, "height": 4.0}
            key = "parts" if fmt == "parts" else "items"
            return {"room": room, key: []}

        xs = [p.gx for p in self.pieces]
        zs = [p.gz for p in self.pieces]
        pad = 2.0
        room_w = (max(xs) - min(xs)) + pad * 2
        room_d = (max(zs) - min(zs)) + pad * 2
        cx_off = (max(xs) + min(xs)) / 2.0
        cz_off = (max(zs) + min(zs)) / 2.0
        room = {"width": float(room_w), "depth": float(room_d), "height": 4.0}

        out = []
        for p in self.pieces:
            # Use multi-cell footprint if the piece occupies more than one cell
            if len(p.cells) > 1:
                cell_xs = [c[0] for c in p.cells]
                cell_zs = [c[2] for c in p.cells]
                w = float(max(cell_xs) - min(cell_xs) + 1)
                d = float(max(cell_zs) - min(cell_zs) + 1)
                h = 1.4  # fence/wall-ish default for multi-cell
            else:
                w, d, h = default_bbox.get(p.type, (1.0, 1.0, 1.0))

            # Centered coords (relative to room center)
            rel_x = float(p.gx) - cx_off
            rel_z = float(p.gz) - cz_off

            entry = {
                "name": f"{p.type}_{p.id}",
                "w": float(w),
                "d": float(d),
                "h": float(h),
            }
            if fmt == "parts":
                # braille_view: centered x,z (no y — top view is 2D)
                entry["x"] = rel_x
                entry["z"] = rel_z
            else:
                # layout_compare: corner-positioned x,z, centered y
                entry["x"] = rel_x - w / 2
                entry["z"] = rel_z - d / 2
                entry["y"] = h / 2
            out.append(entry)

        key = "parts" if fmt == "parts" else "items"
        return {"room": room, key: out}

    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "pieces": [
                {
                    "id": p.id,
                    "type": p.type,
                    "label": p.label,
                    "gx": p.gx,
                    "gy": p.gy,
                    "gz": p.gz,
                    "rot": p.rot,
                    "group": p.group,
                    "family": p.family,
                    "meta": p.meta,
                }
                for p in self.pieces
            ],
            "meta": self.meta,
            "trace": self.trace,
        }

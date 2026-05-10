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

    def to_ascii(self, include_legend: bool = False, show_axes: bool = True, include_warnings: bool = True, symbol_overrides: Dict[str, str] | None = None):
        from .exporters import result_to_ascii
        return result_to_ascii(
            self,
            include_legend=include_legend,
            show_axes=show_axes,
            include_warnings=include_warnings,
            symbol_overrides=symbol_overrides,
        )

    def to_layout(self, fmt: str = "parts") -> List[Dict[str, Any]]:
        """Convert pieces to verifier-compatible layout dicts.

        fmt='parts'  → {x, z, w, d, h} centered coords — braille_view format
        fmt='items'  → {x, z, w, d, h} corner-positioned — layout_compare format

        All pieces are treated as 1×1 footprint, height 1.  Override h in caller
        if the verifier needs actual heights.
        """
        if fmt not in ("parts", "items"):
            raise ValueError(f"fmt must be 'parts' or 'items', got {fmt!r}")
        out = []
        for p in self.pieces:
            if fmt == "parts":
                x, z = float(p.gx), float(p.gz)
            else:
                x, z = float(p.gx) - 0.5, float(p.gz) - 0.5
            out.append({
                "id": p.id,
                "type": p.type,
                "label": p.label,
                "x": x,
                "z": z,
                "w": 1.0,
                "d": 1.0,
                "h": 1.0,
            })
        return out

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

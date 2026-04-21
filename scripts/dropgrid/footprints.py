from __future__ import annotations
from typing import Dict, List, Tuple

Cell3 = Tuple[int, int, int]

BASE_FOOTPRINTS: Dict[str, List[Cell3]] = {
    "road": [(0,0,0)],
    "tree": [(0,0,0)],
    "log": [(0,0,0), (1,0,0)],
    "lantern": [(0,0,0)],
    "rubble": [(0,0,0)],
    "post": [(0,0,0)],
    "gate": [(0,0,0), (1,0,0)],
    "wall": [(0,0,0), (1,0,0)],
    "fence": [(0,0,0), (1,0,0)],
    "door": [(0,0,0)],
    "house": [(0,0,0), (1,0,0), (0,0,1), (1,0,1)],
    "table": [(0,0,0), (1,0,0), (0,0,1), (1,0,1)],
    "chair": [(0,0,0)],
    "bench": [(0,0,0), (1,0,0)],
    "tower": [(0,0,0), (1,0,0), (0,0,1), (1,0,1)],
    "campfire": [(0,0,0)],
    "altar": [(0,0,0), (1,0,0)],
    "fountain": [(0,0,0), (1,0,0), (0,0,1), (1,0,1)],
    "wagon": [(0,0,0), (1,0,0), (2,0,0)],
    "statue": [(0,0,0)],
    "plinth": [(0,0,0), (1,0,0), (0,0,1), (1,0,1)],
}

def rotate_cells(cells: List[Cell3], rot: int) -> List[Cell3]:
    out: List[Cell3] = []
    for x, y, z in cells:
        r = rot % 4
        if r == 0:
            out.append((x, y, z))
        elif r == 1:
            out.append((-z, y, x))
        elif r == 2:
            out.append((-x, y, -z))
        else:
            out.append((z, y, -x))
    minx = min(x for x, _, _ in out)
    minz = min(z for _, _, z in out)
    return [(x - minx, y, z - minz) for x, y, z in out]

def cells_for(piece_type: str, rot: int = 0) -> List[Cell3]:
    return rotate_cells(BASE_FOOTPRINTS.get(piece_type, [(0,0,0)]), rot)

def footprint_span(piece_type: str) -> int:
    cells = BASE_FOOTPRINTS.get(piece_type, [(0,0,0)])
    maxx = max(x for x, _, _ in cells)
    maxz = max(z for _, _, z in cells)
    return max(maxx, maxz) + 1

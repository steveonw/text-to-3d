from __future__ import annotations

SYMBOLS = {
    'road': '=',
    'tree': 't',
    'log': '-',
    'lantern': 'L',
    'rubble': '.',
    'wall': '#',
    'fence': 'H',
    'gate': 'G',
    'door': 'D',
    'house': 'U',
    'tower': 'W',
    'campfire': '*',
    'table': 'T',
    'chair': 'C',
    'bench': 'B',
    'altar': 'A',
    'fountain': 'F',
    'wagon': 'V',
    'statue': 'S',
    'plinth': 'P',
    'stall': 'S',
    'crate': 'c',
    'barrel': 'b',
    'bush': 'o',
    'rock': 'r',
    'post': 'p',
    'flag': 'f',
}

# Height tiers: 0=flat, 1=short, 2=medium, 3=tall
HEIGHTS = {
    'road': 0, 'rubble': 0, 'log': 0, 'floor': 0,
    'campfire': 1, 'bench': 1, 'chair': 1, 'table': 1, 'plinth': 1,
    'crate': 1, 'barrel': 1, 'rock': 1, 'bush': 1,
    'lantern': 2, 'fence': 2, 'wall': 2, 'door': 2, 'gate': 2,
    'altar': 2, 'fountain': 2, 'wagon': 2, 'statue': 2, 'post': 2,
    'stall': 2, 'flag': 2,
    'tree': 3, 'house': 3, 'tower': 3,
}
HEIGHT_CHARS = ['░', '▒', '▓', '█']  # index = height tier 0-3
HEIGHT_LABELS = ['flat', 'short', 'medium', 'tall']

# Box-drawing chars for MA zone cell boundaries.
# Key: (open_N, open_S, open_E, open_W) where True = that neighbor is NOT a MA cell.
_BOX_CHARS = {
    (False, False, False, False): '░',  # interior — all neighbors are MA
    (True,  False, False, False): '─',  # top edge
    (False, True,  False, False): '─',  # bottom edge
    (False, False, True,  False): '│',  # right edge
    (False, False, False, True ): '│',  # left edge
    (True,  False, False, True ): '┌',  # top-left corner
    (True,  False, True,  False): '┐',  # top-right corner
    (False, True,  False, True ): '└',  # bottom-left corner
    (False, True,  True,  False): '┘',  # bottom-right corner
    (True,  True,  False, False): '│',  # single-cell-wide E-W strip
    (False, False, True,  True ): '─',  # single-cell-wide N-S strip
    (True,  True,  True,  False): '├',  # W-connected cap
    (True,  True,  False, True ): '┤',  # E-connected cap
    (True,  False, True,  True ): '┬',  # S-connected cap
    (False, True,  True,  True ): '┴',  # N-connected cap
    (True,  True,  True,  True ): '░',  # isolated single cell
}


def _symbol_for(piece, symbol_overrides=None):
    symbol_overrides = symbol_overrides or {}
    if piece.type in symbol_overrides:
        return symbol_overrides[piece.type]
    if piece.meta.get("symbol"):
        return piece.meta["symbol"]
    return SYMBOLS.get(piece.type, piece.type[:1].upper())


def _ma_box_char(x, z, ma_set):
    """Return a box-drawing char for a MA boundary cell based on its neighbors."""
    key = (
        (x, z - 1) not in ma_set,  # N open?
        (x, z + 1) not in ma_set,  # S open?
        (x + 1, z) not in ma_set,  # E open?
        (x - 1, z) not in ma_set,  # W open?
    )
    return _BOX_CHARS.get(key, '░')


def result_to_ascii(
    result,
    include_legend=False,
    show_axes=True,
    include_warnings=True,
    symbol_overrides=None,
    show_borders=True,
    show_heights=False,
):
    """Render the scene as a top-down ASCII grid.

    show_borders — use box-drawing chars (┌─┐│└┘ etc.) for MA zone edges.
                   Interior MA cells stay ░. Default True.
    show_heights — append a second grid after the main one using block chars
                   (░▒▓█) to encode object height tier. Default False.
    """
    pieces = result.pieces
    if not pieces:
        return ""
    maxx = max([p.gx + max(dx for dx, _, _ in p.cells) for p in pieces] + [0]) + 3
    maxz = max([p.gz + max(dz for _, _, dz in p.cells) for p in pieces] + [0]) + 3
    grid = [['·' for _ in range(maxx)] for _ in range(maxz)]

    ma_cells_raw = result.meta.get('ma_cells', [])
    ma_set = set(map(tuple, ma_cells_raw))

    for x, z in ma_cells_raw:
        if 0 <= z < maxz and 0 <= x < maxx:
            grid[z][x] = _ma_box_char(x, z, ma_set) if show_borders else '░'

    for p in pieces:
        ch = _symbol_for(p, symbol_overrides)
        for dx, _, dz in p.cells:
            x = p.gx + dx
            z = p.gz + dz
            if 0 <= z < maxz and 0 <= x < maxx:
                grid[z][x] = ch

    for c in result.meta.get('connections', []):
        a = c['from'] if isinstance(c, dict) else c[0]
        b = c['to'] if isinstance(c, dict) else c[1]
        pa = next((p for p in pieces if p.id == a), None)
        pb = next((p for p in pieces if p.id == b), None)
        if pa and pb:
            mx = (pa.gx + pb.gx) // 2
            mz = (pa.gz + pb.gz) // 2
            if 0 <= mz < maxz and 0 <= mx < maxx and grid[mz][mx] in {'·', '░'}:
                grid[mz][mx] = '='

    lines = []
    if include_warnings:
        warnings = result.meta.get('warnings', [])
        for w in warnings:
            lines.append(f'⚠ {w}')
        if warnings:
            lines.append('')

    for z, row in enumerate(grid):
        lines.append((f"{z:02d} " if show_axes else "") + ''.join(row))

    if include_legend:
        seen = {}
        for p in pieces:
            seen[_symbol_for(p, symbol_overrides)] = p.type
        lines.append("")
        lines.append("Legend: " + " ".join(f"{k}={v}" for k, v in sorted(seen.items())) + " ░=MA")
        if show_borders:
            lines.append("        ┌─┐│└─┘ = MA zone border")

    if show_heights:
        # Build a height grid using block chars
        hgrid = [['·' for _ in range(maxx)] for _ in range(maxz)]
        for x, z in ma_cells_raw:
            if 0 <= z < maxz and 0 <= x < maxx:
                hgrid[z][x] = '░'  # MA zone floor
        # Build a piece-id lookup for height
        piece_at = {}
        for p in pieces:
            tier = HEIGHTS.get(p.type, 2)  # unknown types default to medium
            for dx, _, dz in p.cells:
                piece_at[(p.gx + dx, p.gz + dz)] = tier
        for (px, pz), tier in piece_at.items():
            if 0 <= pz < maxz and 0 <= px < maxx:
                hgrid[pz][px] = HEIGHT_CHARS[min(tier, 3)]
        lines.append("")
        lines.append("Height: " + "  ".join(f"{HEIGHT_CHARS[i]}={HEIGHT_LABELS[i]}" for i in range(4)))
        for z, row in enumerate(hgrid):
            lines.append((f"{z:02d} " if show_axes else "") + ''.join(row))

    return "\n".join(lines)

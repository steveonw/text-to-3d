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
}

def _symbol_for(piece, symbol_overrides=None):
    symbol_overrides = symbol_overrides or {}
    if piece.type in symbol_overrides:
        return symbol_overrides[piece.type]
    if piece.meta.get("symbol"):
        return piece.meta["symbol"]
    return SYMBOLS.get(piece.type, piece.type[:1].upper())

def result_to_ascii(result, include_legend=False, show_axes=True, include_warnings=True, symbol_overrides=None):
    pieces = result.pieces
    if not pieces:
        return ""
    maxx = max([p.gx + max(dx for dx, _, _ in p.cells) for p in pieces] + [0]) + 3
    maxz = max([p.gz + max(dz for _, _, dz in p.cells) for p in pieces] + [0]) + 3
    grid = [['·' for _ in range(maxx)] for _ in range(maxz)]
    for x, z in result.meta.get('ma_cells', []):
        if 0 <= z < maxz and 0 <= x < maxx:
            grid[z][x] = '░'
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
    return "\n".join(lines)

from __future__ import annotations
from math import cos, sin, pi
from .models import Piece, SceneResult
from .footprints import cells_for

GW = 30
GD = 30

FAMILY = {
    'road':'path',
    'tree':'flora',
    'log':'prop',
    'lantern':'prop',
    'rubble':'prop',
    'wall':'barrier',
    'fence':'barrier',
    'gate':'barrier',
    'door':'attachable',
    'house':'building',
    'tower':'anchor',
    'campfire':'anchor',
    'table':'host',
    'chair':'attachable',
    'bench':'attachable',
    'altar':'host',
    'fountain':'host',
    'wagon':'prop',
    'statue':'host',
    'plinth':'host',
}

DIRS = [(0,-1),(1,0),(0,1),(-1,0)]  # N,E,S,W

def make_ma(anchor, radius):
    ma = set()
    cx, cz = anchor
    for x in range(cx - radius, cx + radius + 1):
        for z in range(cz - radius, cz + radius + 1):
            if (x - cx) * (x - cx) + (z - cz) * (z - cz) <= radius * radius:
                ma.add((x, z))
    return ma

def fits(occ, ma, cells, gx, gz):
    for dx, _, dz in cells:
        x = gx + dx
        z = gz + dz
        if x < 0 or z < 0 or x >= GW or z >= GD:
            return False, 'oob'
        if (x, z) in ma:
            return False, 'ma'
        if (x, z) in occ:
            return False, 'occ'
    return True, 'ok'

def place_piece(pieces, occ, next_id, tp, label, gx, gz, rot=0):
    cells = cells_for(tp, rot)
    p = Piece(id=next_id, type=tp, label=label, gx=gx, gy=0, gz=gz, rot=rot, cells=cells, group=label, family=FAMILY.get(tp,''), meta={})
    for dx, _, dz in cells:
        occ[(gx + dx, gz + dz)] = p.id
    pieces.append(p)
    return next_id + 1, p

def ring_slots(cx, cz, r, n, arc=1.0):
    span = max(0.05, min(1.0, arc)) * 2 * pi
    start = -pi / 2 - span / 2
    return [
        (round(cx + cos(start + i * span / max(1, n)) * r), round(cz + sin(start + i * span / max(1, n)) * r), start + i * span / max(1, n))
        for i in range(max(1, n))
    ]

def rect_slots(cx, cz, rx, rz, n, arc=1.0):
    pts = []
    for x in range(cx-rx, cx+rx+1):
        pts.append((x, cz-rz, 0.0))
    for z in range(cz-rz+1, cz+rz+1):
        pts.append((cx+rx, z, pi/2))
    for x in range(cx+rx-1, cx-rx-1, -1):
        pts.append((x, cz+rz, pi))
    for z in range(cz+rz-1, cz-rz, -1):
        pts.append((cx-rx, z, -pi/2))
    if not pts:
        return [(cx, cz, 0.0)]
    use_n = max(1, int(len(pts) * max(0.05, min(1.0, arc))))
    pts = pts[:use_n]
    return [pts[int(i * len(pts) / max(1, n)) % len(pts)] for i in range(max(1, n))]

def side_offsets(side, distance):
    if side == 'left':
        return [(-distance, 0), (0, -distance)]
    if side == 'right':
        return [(distance, 0), (0, distance)]
    return [(-distance, 0), (distance, 0), (0, -distance), (0, distance)]

def table_sockets(host):
    x, z = host.gx, host.gz
    return [
        (x, z-1, 2), (x+1, z-1, 2),
        (x+2, z, 3), (x+2, z+1, 3),
        (x, z+2, 0), (x+1, z+2, 0),
        (x-1, z, 1), (x-1, z+1, 1),
    ]

def barrier_face_sockets(host):
    if host.rot % 2 == 0:  # east-west
        return [(host.gx, host.gz-1, 2), (host.gx+1, host.gz-1, 2), (host.gx, host.gz+1, 0), (host.gx+1, host.gz+1, 0)]
    return [(host.gx-1, host.gz, 1), (host.gx-1, host.gz+1, 1), (host.gx+1, host.gz, 3), (host.gx+1, host.gz+1, 3)]

def classify_and_connect(pieces):
    pos = {}
    for p in pieces:
        pos[(p.gx, p.gz)] = p
    conns = []
    connectable = {'barrier', 'path'}
    for p in pieces:
        if p.family not in connectable:
            continue
        cnt = 0
        for dx, dz, name in [(1,0,'E'),(-1,0,'W'),(0,1,'S'),(0,-1,'N')]:
            q = pos.get((p.gx + dx, p.gz + dz))
            if q and q.family == p.family:
                # gate guardrail: only straight variants
                if p.type == 'gate' and q.type == 'gate':
                    if name in {'N','S'} and p.rot % 2 == 0:
                        continue
                    if name in {'E','W'} and p.rot % 2 == 1:
                        continue
                if p.id < q.id:
                    conns.append({'from': p.id, 'to': q.id, 'dir': name})
                cnt += 1
        if p.type == 'gate':
            if any(c['from'] == p.id and c['dir'] in {'E','W'} or c['to'] == p.id and c['dir'] in {'E','W'} for c in conns):
                variant = 'EW'
            elif any(c['from'] == p.id and c['dir'] in {'N','S'} or c['to'] == p.id and c['dir'] in {'N','S'} for c in conns):
                variant = 'NS'
            else:
                variant = 'isolated'
            p.meta['variant'] = variant
        else:
            p.meta['variant'] = 'isolated' if cnt == 0 else 'connected'
        p.meta['connection_count'] = cnt
    return conns

def _ma_radius(spec):
    ma = spec.get('ma')
    if isinstance(ma, dict):
        return int(ma.get('radius') or 0)
    return int(ma or 0)

def _ma_mode(spec):
    ma = spec.get('ma')
    if isinstance(ma, dict):
        return ma.get('mode', 'hard')
    return 'hard' if ma else None

def _path_heading(name):
    return {'north':0,'east':1,'south':2,'west':3}[name]

def _turn_left(h): return (h - 1) % 4
def _turn_right(h): return (h + 1) % 4

def _edge_penalty(x, z, margin=3):
    d = min(x, z, GW - 1 - x, GD - 1 - z)
    return max(0, margin - d)

def _follower_shoulder_score(occ, ma, x, z, heading, shoulder_dist):
    if shoulder_dist <= 0:
        return 0
    if heading % 2 == 0:
        checks = [(x - shoulder_dist, z), (x + shoulder_dist, z)]
    else:
        checks = [(x, z - shoulder_dist), (x, z + shoulder_dist)]
    score = 0
    for sx, sz in checks:
        ok, why = fits(occ, ma, [(0,0,0)], sx, sz)
        if ok:
            score += 2
        elif why == 'oob':
            score -= 2
        elif why == 'ma':
            score -= 1
    return score

def _choose_next_path_cell(occ, ma, x, z, heading, straight_bias=3, shoulder_dist=0, prev_turn=0, wobble=0.0):
    candidates = []
    for turn, h in [(0, heading), (-1, _turn_left(heading)), (1, _turn_right(heading))]:
        dx, dz = DIRS[h]
        nx, nz = x + dx, z + dz
        ok, why = fits(occ, ma, [(0,0,0)], nx, nz)
        score = -999 if not ok else 10
        if ok:
            score += straight_bias if turn == 0 else 0
            score -= 2 if turn and turn == prev_turn else 0
            score -= _edge_penalty(nx, nz, margin=4) * 3
            near_ma = any((nx + mx, nz + mz) in ma for mx, mz in [(-1,0),(1,0),(0,-1),(0,1)])
            if near_ma:
                score -= 2
            score += _follower_shoulder_score(occ, ma, nx, nz, h, shoulder_dist)
            if wobble and turn != 0:
                score += 1
        candidates.append((score, turn, h, nx, nz, why))
    candidates.sort(reverse=True, key=lambda t: (t[0], -abs(t[1])))
    return candidates[0], candidates

def solve_compiled(spec, seed=42, debug=False):
    pieces = []
    trace = []
    occ = {}
    warnings = list(spec.get('warnings', []))

    anchor_type = spec['anchor']['type']
    anchor_label = spec['anchor']['label']
    next_id = 1
    ax, az = (14, 12)
    next_id, anchor = place_piece(pieces, occ, next_id, anchor_type, anchor_label, ax, az, 0)
    ma = make_ma((ax, az), _ma_radius(spec))

    road_shoulder = 0
    for obj in spec['objects']:
        if obj.get('target') == 'road':
            road_shoulder = max(road_shoulder, int(obj.get('distance', 1)))

    for obj in spec['objects']:
        tp = obj['type']
        count = obj.get('count', 1)
        label = obj.get('label', tp)

        # DISPATCH BY INTENT, NOT TYPE
        # 1. Has 'shape' → motif emitter (any type)
        # 2. Has 'from'+'heading' → path turtle (any type)
        # 3. Has 'target' → follow/attach (any type)
        # 4. Has 'radius' only → scatter
        # 5. Fallback → scatter

        has_shape = 'shape' in obj
        has_path = 'from' in obj and 'heading' in obj
        has_target = 'target' in obj and not has_shape
        has_scatter = not has_shape and not has_path and not has_target

        # scatter objects (radius only, no shape/target/path)
        if has_scatter and ('radius' in obj or tp == 'rubble'):
            pts = [(ax+12,az), (ax-12,az+3), (ax+1,az+13), (ax-10, az-8)]
            placed = 0
            for i in range(count):
                x, z = pts[i % len(pts)]
                ok, why = fits(occ, set(), cells_for(tp, 0), x, z)
                trace.append({'phase':'emit','type':tp,'why':why,'try':(x,z)})
                if ok:
                    next_id, p = place_piece(pieces, occ, next_id, tp, f"{label}_{placed}", x, z, 0)
                    if obj.get('symbol'):
                        p.meta['symbol'] = obj['symbol']
                    placed += 1
            continue

        # motif emitter — ANY type with 'shape' in intent
        if has_shape:
            shape = obj.get('shape', 'circle')
            radius = obj.get('radius', 5)
            clusters = obj.get('clusters', count)
            arc = obj.get('arc', 1.0)
            if shape == 'rectangle':
                slots = rect_slots(ax, az, radius, obj.get('distance', radius), clusters, arc=arc)
            elif shape == 'square':
                slots = rect_slots(ax, az, radius, radius, clusters, arc=arc)
            else:
                slots = ring_slots(ax, az, radius, clusters, arc=arc)

            spread = obj.get('spread', 0)
            offs = [(0,0),(1,0),(0,1),(-1,0),(0,-1),(1,1),(-1,-1)]
            for i in range(count):
                sx, sz, ang = slots[i % len(slots)]
                k = i // len(slots)
                ox, oz = offs[k % len(offs)] if spread else (0,0)
                # rotate offset by slot to avoid identical L-shapes in every cluster
                r = (i % len(slots)) % 4
                if r == 1:
                    ox, oz = -oz, ox
                elif r == 2:
                    ox, oz = -ox, -oz
                elif r == 3:
                    ox, oz = oz, -ox

                if tp == 'house':
                    if sx > ax: ox -= 2
                    elif sx < ax: ox += 2
                    if sz > az: oz -= 2
                    elif sz < az: oz += 2

                gx, gz = sx + ox, sz + oz
                rot = 0 if abs(cos(ang)) >= abs(sin(ang)) else 1
                if tp in {'gate','door','chair','bench','lantern'} and shape == 'circle':
                    if sx < ax: rot = 1
                    elif sx > ax: rot = 3
                    elif sz < az: rot = 2
                    else: rot = 0

                tries = [(gx,gz),(gx+1,gz),(gx-1,gz),(gx,gz+1),(gx,gz-1)]
                for tx, tz in tries:
                    ok, why = fits(occ, ma, cells_for(tp, rot), tx, tz)
                    trace.append({'phase':'emit','type':tp,'why':why,'try':(tx,tz)})
                    if ok:
                        next_id, p = place_piece(pieces, occ, next_id, tp, f"{label}_{i}", tx, tz, rot)
                        if obj.get('symbol'):
                            p.meta['symbol'] = obj['symbol']
                        break
            continue

        # corridor turtle — ANY type with 'from'+'heading' in intent
        if has_path:
            heading = _path_heading(obj.get('heading', 'south'))
            dx, dz = DIRS[heading]
            start_offset = max(3, _ma_radius(spec) + 1)
            prev_turn = 0
            x, z = ax + dx * (start_offset - 1), az + dz * (start_offset - 1)
            wobble = float(obj.get('wobble', 0.0))
            for i in range(count):
                best, candidates = _choose_next_path_cell(
                    occ, ma, x, z, heading,
                    straight_bias=3,
                    shoulder_dist=road_shoulder,
                    prev_turn=prev_turn,
                    wobble=wobble,
                )
                for cscore, cturn, ch, cx, cz, cwhy in candidates:
                    trace.append({'phase':'place','type':tp,'why':cwhy,'try':(cx,cz),'score':cscore,'heading':ch})
                score, turn, heading, nx, nz, why = best
                if score <= -999:
                    break
                rot = 1 if heading in (0,2) else 0
                next_id, p = place_piece(pieces, occ, next_id, tp, f"{label}_{i}", nx, nz, rot)
                if obj.get('symbol'):
                    p.meta['symbol'] = obj['symbol']
                x, z = nx, nz
                prev_turn = turn
            continue

        # follow/attach — ANY type with 'target' in intent (and no 'shape')
        if has_target:
            target = obj.get('target', 'road')
            roads = [p for p in pieces if p.type == target]
            distance = obj.get('distance', 2)
            spacing = max(1, obj.get('spacing', 1))
            side = obj.get('side', 'any')
            placed = 0
            for idx, host in enumerate(roads):
                if idx % spacing != 0 or placed >= count:
                    continue
                if side == 'any' and host.rot % 2 == 1:
                    offsets = [(-distance,0),(distance,0),(-distance-1,0),(distance+1,0)]
                elif side == 'any' and host.rot % 2 == 0:
                    offsets = [(0,-distance),(0,distance),(0,-distance-1),(0,distance+1)]
                else:
                    offsets = side_offsets(side, distance)
                cand = []
                for ox, oz in offsets:
                    tx, tz = host.gx + ox, host.gz + oz
                    rot = 1 if tp == 'log' and abs(ox) > 0 else 0
                    ok, why = fits(occ, ma, cells_for(tp, rot), tx, tz)
                    edge_pen = _edge_penalty(tx, tz, margin=3)
                    near_ma = 1 if any((tx+mx,tz+mz) in ma for mx,mz in [(-1,0),(1,0),(0,-1),(0,1)]) else 0
                    score = (10 if ok else -999) - edge_pen * 2 - near_ma * 2
                    cand.append((score, tx, tz, rot, why))
                cand.sort(reverse=True)
                for score, tx, tz, rot, why in cand:
                    trace.append({'phase':'attach','type':tp,'why':why,'try':(tx,tz),'score':score})
                    if score <= -999:
                        continue
                    next_id, p = place_piece(pieces, occ, next_id, tp, f"{label}_{placed}", tx, tz, rot)
                    if obj.get('symbol'):
                        p.meta['symbol'] = obj['symbol']
                    placed += 1
                    break
            continue

        # socket attachments
        if tp in {'chair','bench','door'}:
            target = obj.get('target', 'table' if tp in {'chair','bench'} else 'wall')
            hosts = [p for p in pieces if p.type == target or p.group == target or p.label == target]
            placed = 0
            sockets = []
            for host in hosts:
                if host.type in {'table','altar','fountain','plinth'}:
                    sockets.extend([(host, sx, sz, rot) for sx, sz, rot in table_sockets(host)])
                elif host.family == 'barrier':
                    sockets.extend([(host, sx, sz, rot) for sx, sz, rot in barrier_face_sockets(host)])
            for host, sx, sz, rot in sockets:
                if placed >= count:
                    break
                ok, why = fits(occ, ma, cells_for(tp, rot), sx, sz)
                trace.append({'phase':'socket','type':tp,'why':why,'try':(sx,sz),'host':host.label})
                if not ok:
                    continue
                next_id, p = place_piece(pieces, occ, next_id, tp, f"{label}_{placed}", sx, sz, rot)
                p.meta['host_label'] = host.label
                p.meta['socket_class'] = 'edge' if host.family != 'barrier' else 'wall_face'
                if obj.get('symbol'):
                    p.meta['symbol'] = obj['symbol']
                placed += 1
            continue

    conns = classify_and_connect(pieces)
    return SceneResult(
        pieces=pieces,
        meta={
            'connections': conns,
            'ma_cells': sorted(list(ma)),
            'warnings': warnings,
            'ma_mode': _ma_mode(spec) or 'hard',
        },
        trace=trace,
    )

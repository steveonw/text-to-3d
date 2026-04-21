from __future__ import annotations

from .layout_config import LayoutConfig, DEFAULT_CONFIG
from .layout_compiler import compile_layout_dsl, compile_emitter_intents_to_legacy_spec
from .solver import solve_compiled, classify_and_connect, _ma_radius, make_ma
from .models import SceneResult, Piece
from .topology import (
    build_rect_topology,
    apply_gate_edit,
    enumerate_slots,
    rank_slots,
    CARDINAL_YAW,
)


def _piece_center(piece):
    xs = [piece.gx + dx for dx, _, _ in piece.cells]
    zs = [piece.gz + dz for _, _, dz in piece.cells]
    return round(sum(xs) / len(xs)), round(sum(zs) / len(zs))


def _piece_cells2(piece):
    return {(piece.gx + dx, piece.gz + dz) for dx, _, dz in piece.cells}


def _next_piece_id(result: SceneResult) -> int:
    return max((p.id for p in result.pieces), default=0) + 1


def _anchor_piece(result: SceneResult, spec: dict):
    label = spec.get("anchor", {}).get("label")
    for p in result.pieces:
        if p.label == label:
            return p
    return result.pieces[0] if result.pieces else None


def _locate_rect_origin(anchor_piece, width: int, height: int):
    if anchor_piece is None:
        return 14 - width // 2, 12 - height // 2
    return int(anchor_piece.gx - width // 2), int(anchor_piece.gz - height // 2)


def _host_family(kind: str) -> str:
    if kind in {"wall", "fence", "hedge", "gate"}:
        return "barrier"
    if kind in {"road", "bridge", "dock"}:
        return "path"
    return ""


def _make_piece(piece_id: int, kind: str, label: str, group: str, gx: int, gz: int, rot: int, *,
                family: str | None = None, cells=None, meta=None):
    return Piece(
        id=piece_id,
        type=kind,
        label=label,
        gx=gx,
        gy=0,
        gz=gz,
        rot=rot,
        cells=list(cells or [(0, 0, 0)]),
        group=group,
        family=family or _host_family(kind),
        meta=meta or {},
    )


def _build_rect_topologies_from_spec(spec: dict):
    topologies = {}
    host_meta = dict(spec.get("layout_host_topology") or {})
    hosts = list(spec.get("layout_hosts_to_emit") or host_meta.keys())
    ax, az = (14, 12)
    for host_id in hosts:
        meta = host_meta.get(host_id, {})
        if meta.get("shape") != "rect_perimeter":
            continue
        width = int(meta.get("width", DEFAULT_CONFIG.DEFAULT_RECT_PERIMETER_SIZE[0]))
        height = int(meta.get("height", DEFAULT_CONFIG.DEFAULT_RECT_PERIMETER_SIZE[1]))
        ox, oz = int(ax - width // 2), int(az - height // 2)
        topologies[host_id] = build_rect_topology(
            host_id=host_id,
            width=width,
            height=height,
            origin=(ox, oz),
            thickness=float(meta.get("thickness", 1.0)),
        )
    return topologies


def _apply_gate_ops_to_topologies(topologies: dict, spec: dict, result: SceneResult):
    gate_lookup = {}
    trace = {"hosts": {}, "gate_ops": [], "attach_ops": [], "center_ops": []}
    for host_id, top in topologies.items():
        trace["hosts"][host_id] = {
            "shape": "rect_perimeter",
            "origin": [top.origin_x, top.origin_z],
            "width": top.width,
            "height": top.height,
        }
    for op in list(spec.get("layout_special_ops") or []):
        if op.get("type") != "gate_opening":
            continue
        host_id = op.get("target_group")
        top = topologies.get(host_id)
        if not top:
            result.meta.setdefault("warnings", []).append(f"gate_opening: no topology host '{host_id}'")
            continue
        side = op.get("side") or "south"
        span = int(op.get("span", 2))
        gate_label = op.get("gate_label", "gate")
        try:
            edit = apply_gate_edit(top, side, span, gate_label)
            trace["gate_ops"].append({
                "gate": gate_label,
                "host": host_id,
                "side": side,
                "span": span,
                "opening_indices": list(edit.opening_indices),
                "shoulder_indices": list(edit.shoulder_indices),
            })
        except Exception as e:
            result.meta.setdefault("errors", []).append({
                "error": "gate_opening",
                "label": gate_label,
                "message": f"ERROR: gate_opening failed on {host_id}:{side}: {e}",
                "suggestion": "enlarge host or move gate away from corners.",
            })
            continue
        gate_lookup[gate_label] = (top, gate_label)
    return gate_lookup, trace


def _emit_topology_hosts(result: SceneResult, spec: dict, topologies: dict):
    host_meta = dict(spec.get("layout_host_topology") or {})
    occ = {cell for p in result.pieces for cell in _piece_cells2(p)}
    ma = make_ma((14, 12), _ma_radius(spec)) if _ma_radius(spec) else set()
    next_id = _next_piece_id(result)
    emitted = []
    for host_id, top in topologies.items():
        kind = host_meta.get(host_id, {}).get("kind", "fence")
        for side in ("north", "east", "south", "west"):
            for cell in top.sides[side]:
                if cell.role == "opening":
                    continue
                if (cell.x, cell.z) in ma:
                    result.meta.setdefault("errors", []).append({
                        "error": "ma_overlap",
                        "label": host_id,
                        "message": f"ERROR: topology-emitted host cell landed inside MA zone at {(cell.x, cell.z)}.",
                        "suggestion": "increase perimeter size or move the anchor.",
                    })
                    continue
                piece = _make_piece(
                    next_id,
                    kind,
                    f"{host_id}_{side}_{cell.index}",
                    host_id,
                    cell.x,
                    cell.z,
                    CARDINAL_YAW[side] % 4,
                    family="barrier",
                    cells=[(0, 0, 0)],
                    meta={"topology_emitted": True, "side": side, "role": cell.role},
                )
                result.pieces.append(piece)
                emitted.append(piece)
                occ.add((cell.x, cell.z))
                next_id += 1
        for name, v in top.corners.items():
            if (v.x, v.z) in ma:
                continue
            piece = _make_piece(
                next_id,
                kind,
                f"{host_id}_corner_{name}",
                host_id,
                v.x,
                v.z,
                0,
                family="barrier",
                cells=[(0, 0, 0)],
                meta={"topology_emitted": True, "role": "corner"},
            )
            result.pieces.append(piece)
            emitted.append(piece)
            occ.add((v.x, v.z))
            next_id += 1
    return emitted


def _emit_gate_pieces(result: SceneResult, spec: dict, topologies: dict, gate_lookup: dict):
    next_id = _next_piece_id(result)
    emitted = []
    for op in list(spec.get("layout_special_ops") or []):
        if op.get("type") != "gate_opening":
            continue
        host_id = op.get("target_group")
        top = topologies.get(host_id)
        gate_label = op.get("gate_label", "gate")
        if not top:
            continue
        slots = enumerate_slots(top, "opening", gate_label=gate_label)
        if not slots:
            continue
        slot = slots[0]
        piece = _make_piece(
            next_id,
            op.get("kind", "gate"),
            gate_label,
            gate_label,
            int(round(slot.x)),
            int(round(slot.z)),
            slot.yaw % 4,
            family="barrier",
            cells=[(0, 0, 0)],
            meta={"special_op": "gate_opening_topology", "requested_side": op.get("side"), "picked_from_slot_id": slot.slot_id},
        )
        result.pieces.append(piece)
        emitted.append(piece)
        next_id += 1
    return emitted


def _resolve_near_ref(result: SceneResult, near_label: str | None, topologies: dict, gate_lookup: dict):
    if not near_label:
        return None
    if near_label in gate_lookup:
        top, gate_label = gate_lookup[near_label]
        slots = enumerate_slots(top, "opening", gate_label=gate_label)
        if slots:
            return slots[0].point()
    near_pieces = [p for p in result.pieces if p.label == near_label or p.group == near_label]
    if near_pieces:
        return _piece_center(near_pieces[0])
    return None


def _choose_face_side(top, near_ref):
    if not near_ref:
        return "exterior"
    x, z = near_ref
    inside = (top.origin_x < x < top.origin_x + top.width - 1 and
              top.origin_z < z < top.origin_z + top.height - 1)
    return "interior" if inside else "exterior"


def _reseat_attach_ops(result: SceneResult, spec: dict, topologies: dict, gate_lookup: dict, trace: dict):
    next_id = _next_piece_id(result)
    # remove provisional follow pieces for attach ops, then recreate deterministically
    provisional_groups = {op.get("label") for op in list(spec.get("layout_attach_ops") or [])}
    result.pieces = [p for p in result.pieces if p.group not in provisional_groups]
    for op in list(spec.get("layout_attach_ops") or []):
        host_id = op.get("target_group")
        top = topologies.get(host_id)
        if not top:
            continue
        family = op.get("socket") or "face"
        if family not in {"face", "edge", "opening"}:
            continue
        near_ref = _resolve_near_ref(result, op.get("near"), topologies, gate_lookup)
        face_side = op.get("face_side") or _choose_face_side(top, near_ref)
        slots = enumerate_slots(top, family, gate_label=op.get("near"), face_side=face_side)
        ranked = rank_slots(slots, near_ref=near_ref, gate_label=op.get("near"), top=top, symmetry_eps=DEFAULT_CONFIG.SYMMETRY_EPSILON)
        want = int(op.get("count", 1))
        if len(ranked) < want:
            result.meta.setdefault("errors", []).append({
                "error": "attach_scarcity",
                "label": op.get("label"),
                "requested": want,
                "available": len(ranked),
                "message": f"ERROR: requested {want} attach placements but only {len(ranked)} legal face slots exist.",
                "suggestion": "reduce count or target a longer host.",
            })
            trace["attach_ops"].append({
                "label": op.get("label"),
                "host": host_id,
                "socket": family,
                "near_ref": near_ref,
                "face_side": face_side,
                "candidate_count": len(ranked),
                "chosen": [],
            })
            continue
        chosen = ranked[:want]
        trace["attach_ops"].append({
            "label": op.get("label"),
            "host": host_id,
            "socket": family,
            "near_ref": near_ref,
            "face_side": face_side,
            "candidate_count": len(ranked),
            "top_slots": [{"slot_id": s.slot_id, "score_terms": dict(s.score_terms), "side": s.side, "index": s.index, "face_side": s.face_side} for s in ranked[: min(5, len(ranked))]],
            "chosen": [s.slot_id for s in chosen],
        })
        for i, slot in enumerate(chosen):
            piece = _make_piece(
                next_id,
                op.get("kind", "torch"),
                f"{op.get('label')}_{i}" if want > 1 else op.get("label"),
                op.get("label"),
                int(round(slot.x)),
                int(round(slot.z)),
                slot.yaw % 4,
                family="attachable",
                cells=[(0, 0, 0)],
                meta={
                    "picked_from_slot_id": slot.slot_id,
                    "score_terms": dict(slot.score_terms),
                    "host_group": host_id,
                    "socket_family": family,
                    "face_side": slot.face_side,
                },
            )
            result.pieces.append(piece)
            next_id += 1


def _place_centers(result: SceneResult, spec: dict, topologies: dict, trace: dict, config: LayoutConfig):
    centers = list(spec.get("layout_fixed_centers") or [])
    if not centers:
        return
    imp_rank = {"primary": 0, "secondary": 1, "background": 2}
    centers.sort(key=lambda c: (imp_rank.get(c.get("importance"), 1), c.get("label", "")))
    occ = {cell for p in result.pieces for cell in _piece_cells2(p)}
    next_id = _next_piece_id(result)

    def moore_ring(cx, cz, r):
        for dz in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if max(abs(dx), abs(dz)) == r:
                    yield (cx + dx, cz + dz)

    for c in centers:
        host = c.get("host")
        top = topologies.get(host)
        if not top:
            continue
        cx = top.origin_x + top.width // 2
        cz = top.origin_z + top.height // 2
        placed = None
        attempts = []
        for r in range(0, config.DEFAULT_CENTER_MAX_NUDGE + 1):
            candidates = [(cx, cz)] if r == 0 else list(moore_ring(cx, cz, r))
            for x, z in candidates:
                attempts.append((x, z))
                if (x, z) in occ:
                    continue
                piece = _make_piece(
                    next_id,
                    c.get("kind", "fountain"),
                    c.get("label"),
                    c.get("host") or c.get("label"),
                    x,
                    z,
                    0,
                    family="host",
                    cells=[(0, 0, 0)],
                    meta={"center_placed": True, "center_radius": r},
                )
                result.pieces.append(piece)
                occ.add((x, z))
                next_id += 1
                placed = piece
                break
            if placed:
                break
        trace["center_ops"].append({
            "label": c.get("label"),
            "host": host,
            "attempts": attempts[:10],
            "placed": [placed.gx, placed.gz] if placed else None,
        })
        if not placed:
            result.meta.setdefault("errors", []).append({
                "error": "center_nudge_exhausted",
                "label": c.get("label"),
                "message": "ERROR: no legal center slot found within maximum nudge radius.",
                "suggestion": "enlarge the host zone or remove competing geometry near the center.",
            })


def _apply_topology_ops(result: SceneResult, spec: dict, topologies: dict, config: LayoutConfig = DEFAULT_CONFIG) -> SceneResult:
    gate_lookup, trace = _apply_gate_ops_to_topologies(topologies, spec, result)
    topo_pieces = _emit_topology_hosts(result, spec, topologies)
    topology_refs = _topology_reference_points(topologies)
    _place_centers(result, spec, topologies, trace, config)
    _emit_gate_pieces(result, spec, topologies, gate_lookup)
    topology_refs = _topology_reference_points(topologies)
    _reseat_attach_ops(result, spec, topologies, gate_lookup, trace)
    conns = classify_and_connect(result.pieces)
    result.meta["connections"] = conns
    result.meta["topology_hosts"] = sorted(topologies.keys())
    result.meta["runtime_trace"] = trace
    result.meta["topology_exports"] = topology_refs
    return result



def _topology_reference_points(topologies: dict):
    refs = {}
    for host_id, top in topologies.items():
        refs[f"{host_id}_center"] = (
            top.origin_x + (top.width - 1) / 2.0,
            top.origin_z + (top.height - 1) / 2.0,
        )
        for gate_label, edit in top.gate_edits.items():
            slots = enumerate_slots(top, "opening", gate_label=gate_label)
            if slots:
                refs[gate_label] = slots[0].point()
            side_track = top.sides.get(edit.side, [])
            shoulders = [c for c in side_track if c.role == "shoulder"]
            for idx, cell in enumerate(shoulders):
                refs[f"{gate_label}_shoulder_{idx}"] = cell.center()
    return refs


def _inject_preplaced_occupancy(pieces):
    occ = {}
    for p in pieces:
        for cell in _piece_cells2(p):
            occ[cell] = p.id
    return occ


def _partition_spec(spec: dict):
    topo_hosts = set(spec.get("layout_hosts_to_emit") or [])
    legacy_spec = dict(spec)
    legacy_spec["objects"] = [obj for obj in list(spec.get("objects") or []) if obj.get("label") not in topo_hosts]
    return topo_hosts, legacy_spec

def solve_layout_dsl(text: str, seed: int = 42, debug: bool = False, config: LayoutConfig = DEFAULT_CONFIG):
    intents = compile_layout_dsl(text, config=config)
    full_spec = compile_emitter_intents_to_legacy_spec(intents, config=config)

    # Phase A: topology first
    topologies = _build_rect_topologies_from_spec(full_spec)
    topo_seed_result = SceneResult(pieces=[], meta={}, trace=[])
    gate_lookup, trace = _apply_gate_ops_to_topologies(topologies, full_spec, topo_seed_result)
    _emit_topology_hosts(topo_seed_result, full_spec, topologies)
    topology_refs = _topology_reference_points(topologies)

    # Phase B: inject occupancy before solver
    pre_pieces = list(topo_seed_result.pieces)
    pre_occ = _inject_preplaced_occupancy(pre_pieces)

    # Phase C: legacy solve with topology refs
    _, legacy_spec = _partition_spec(full_spec)
    result = solve_compiled(legacy_spec, seed=seed, debug=debug, pre_pieces=pre_pieces, pre_occ=pre_occ, reference_points=topology_refs)
    result.meta.setdefault("runtime_phases", []).extend([
        "partition",
        "topology_build",
        "topology_emit",
        "occupancy_inject",
        "legacy_solve",
        "attach_reseat",
    ])

    # Phase D: post topology-dependent placement
    _place_centers(result, full_spec, topologies, trace, config)
    _emit_gate_pieces(result, full_spec, topologies, gate_lookup)
    topology_refs = _topology_reference_points(topologies)
    _reseat_attach_ops(result, full_spec, topologies, gate_lookup, trace)

    conns = classify_and_connect(result.pieces)
    result.meta["connections"] = conns
    result.meta["topology_hosts"] = sorted(topologies.keys())
    result.meta["runtime_trace"] = trace
    result.meta["topology_exports"] = topology_refs
    result.meta["legacy_spec"] = legacy_spec
    result.meta["full_spec"] = full_spec
    return result

from __future__ import annotations

from .layout_config import LayoutConfig, DEFAULT_CONFIG
from .layout_schema import EmitterIntent, LayoutObject
from .layout_normalizer import parse_layout_dsl, normalize_objects, NormalizedObject


def _rect_perimeter_count(config: LayoutConfig) -> int:
    w, h = config.DEFAULT_RECT_PERIMETER_SIZE
    # perimeter cells, corners counted once
    return (2 * w + 2 * h - 4) // config.DEFAULT_PERIMETER_STEP


def _rect_fill_count(config: LayoutConfig) -> int:
    w, h = config.DEFAULT_RECT_FILL_SIZE
    return w * h


def _mode_to_emit(obj: NormalizedObject, config: LayoutConfig) -> dict:
    mode = obj.mode
    if mode == "rect_perimeter":
        return {
            "shape": "rectangle",
            "placement_mode": "motif",
            "radius": config.DEFAULT_RECT_PERIMETER_SIZE[0] // 2,
            "distance": config.DEFAULT_RECT_PERIMETER_SIZE[1] // 2,
            "count": max(obj.count, _rect_perimeter_count(config)),
            "step": config.DEFAULT_PERIMETER_STEP,
        }
    if mode == "circle_perimeter":
        return {
            "shape": "circle",
            "placement_mode": "motif",
            "radius": config.DEFAULT_CIRCLE_PERIMETER_RADIUS,
            "count": max(obj.count, max(8, int(2 * 3.14159 * config.DEFAULT_CIRCLE_PERIMETER_RADIUS))),
        }
    if mode == "rect_fill":
        return {
            "shape": "rect_fill",
            "placement_mode": "scatter",
            "radius": max(config.DEFAULT_RECT_FILL_SIZE),
            "count": max(obj.count, 1 if obj.kind in {"tower","statue","fountain","shrine","plinth","table"} else min(obj.count, _rect_fill_count(config))),
        }
    if mode == "circle_fill":
        return {
            "shape": "circle_fill",
            "placement_mode": "scatter",
            "radius": config.DEFAULT_CIRCLE_FILL_RADIUS,
            "count": obj.count,
        }
    if mode == "line":
        return {
            "shape": "line",
            "placement_mode": "path",
            "count": max(obj.count, config.DEFAULT_LINE_LENGTH),
            "length": config.DEFAULT_LINE_LENGTH,
        }
    if mode == "follow":
        return {
            "shape": "follow",
            "placement_mode": "follow",
            "count": obj.count,
            "spacing": config.DEFAULT_FOLLOW_SPACING,
        }
    if mode == "cluster":
        return {
            "shape": "cluster",
            "placement_mode": "scatter",
            "count": obj.count,
            "radius": config.DEFAULT_CLUSTER_RADIUS,
        }
    if mode == "scatter":
        return {
            "shape": "scatter",
            "placement_mode": "scatter",
            "count": obj.count,
            "radius": config.DEFAULT_RECT_FILL_SIZE[0] // 2,
        }
    if mode == "center":
        return {
            "shape": "fixed_center",
            "placement_mode": "fixed",
            "count": 1,
            "max_nudge": config.DEFAULT_CENTER_MAX_NUDGE,
        }
    if mode == "attach":
        return {
            "shape": "fixed_slots",
            "placement_mode": "attach",
            "count": obj.count,
            "socket": obj.socket,
        }
    raise ValueError(f"unsupported mode {mode}")


def compile_objects_to_emitter_intents(objects: list[LayoutObject], config: LayoutConfig = DEFAULT_CONFIG) -> list[EmitterIntent]:
    normalized = normalize_objects(objects, config=config)
    intents: list[EmitterIntent] = []
    for obj in normalized:
        emit = _mode_to_emit(obj, config)
        relations = {}
        for field in ("target","inside","outside","around","along","near","facing","align","align_ref","socket"):
            val = getattr(obj, field, None)
            if val is not None:
                relations[field] = val
        if "gate_opening" in obj.roles:
            relations["special_op"] = {
                "type": "gate_opening",
                "side": obj.facing,
                "span": config.DEFAULT_GATE_OPENING_SPAN,
            }
        intents.append(EmitterIntent(
            kind=obj.kind,
            label=obj.label,
            count=obj.count,
            emit=emit,
            relations=relations,
            traits=list(obj.traits),
            importance=obj.importance,
        ))
    return intents


def compile_layout_dsl(text: str, config: LayoutConfig = DEFAULT_CONFIG) -> list[EmitterIntent]:
    return compile_objects_to_emitter_intents(parse_layout_dsl(text), config=config)


def _legacy_kind(kind: str) -> str:
    return {
        "hedge": "fence",
        "banner": "torch",  # use attachable placeholder footprint in legacy solver
        "shrine": "fountain",
        "dock": "road",
        "bridge": "road",
    }.get(kind, kind)


def compile_emitter_intents_to_legacy_spec(intents: list[EmitterIntent], config: LayoutConfig = DEFAULT_CONFIG) -> dict:
    """Translate V1.2 emitter intents into the legacy solve_compiled spec shape."""
    warnings: list[str] = []
    if not intents:
        return {
            "anchor": {"type": "tower", "label": "anchor"},
            "ma": None,
            "objects": [],
            "warnings": warnings,
            "layout_special_ops": [],
            "layout_attach_ops": [],
            "layout_host_topology": {},
            "layout_hosts_to_emit": [],
            "layout_fixed_centers": [],
        }

    # choose stable anchor
    anchor_idx = 0
    for i, intent in enumerate(intents):
        if intent.emit.get("placement_mode") == "fixed" and intent.importance == "primary":
            anchor_idx = i
            break
    else:
        for i, intent in enumerate(intents):
            if intent.emit.get("placement_mode") == "fixed":
                anchor_idx = i
                break

    anchor_intent = intents[anchor_idx]
    anchor_type = _legacy_kind(anchor_intent.kind)
    anchor_label = anchor_intent.label

    objects: list[dict] = []
    special_ops: list[dict] = []
    attach_ops: list[dict] = []
    host_topology: dict[str, dict] = {}
    hosts_to_emit: list[str] = []
    fixed_centers: list[dict] = []

    for i, intent in enumerate(intents):
        if i == anchor_idx:
            continue
        kind = _legacy_kind(intent.kind)
        emit = intent.emit
        placement_mode = emit.get("placement_mode")
        rel = dict(intent.relations)

        # topology-managed structural hosts
        if placement_mode == "motif" and emit.get("shape") == "rectangle" and kind in {"wall", "fence", "hedge"}:
            host_topology[intent.label] = {
                "kind": kind,
                "shape": "rect_perimeter",
                "width": int(config.DEFAULT_RECT_PERIMETER_SIZE[0]),
                "height": int(config.DEFAULT_RECT_PERIMETER_SIZE[1]),
                "thickness": 1.0,
            }
            hosts_to_emit.append(intent.label)
            continue

        # true centers handled post-solve
        if placement_mode == "fixed":
            fixed_centers.append({
                "label": intent.label,
                "kind": kind,
                "host": rel.get("inside") or rel.get("target"),
                "importance": intent.importance,
            })
            continue

        obj: dict = {"type": kind, "label": intent.label, "count": intent.count, "placement_mode": placement_mode}

        if placement_mode == "motif":
            shape = emit.get("shape", "circle")
            if shape == "rectangle":
                obj["shape"] = "rectangle"
                obj["radius"] = int(emit.get("radius", config.DEFAULT_RECT_PERIMETER_SIZE[0] // 2))
                obj["distance"] = int(emit.get("distance", config.DEFAULT_RECT_PERIMETER_SIZE[1] // 2))
            elif shape == "circle":
                obj["shape"] = "circle"
                obj["radius"] = int(emit.get("radius", config.DEFAULT_CIRCLE_PERIMETER_RADIUS))
            else:
                obj["shape"] = "circle"
                obj["radius"] = int(emit.get("radius", config.DEFAULT_CIRCLE_PERIMETER_RADIUS))
            obj["count"] = int(emit.get("count", intent.count))
            obj["target"] = rel.get("target") or rel.get("inside") or rel.get("around") or anchor_label

        elif placement_mode == "attach":
            obj["placement_mode"] = "follow"
            obj["target"] = rel.get("target") or anchor_label
            obj["count"] = int(emit.get("count", intent.count))
            obj["distance"] = 1
            obj["spacing"] = 1
            if rel.get("socket") == "opening":
                special_ops.append({
                    "type": "gate_opening",
                    "gate_label": intent.label,
                    "target_group": rel.get("target"),
                    "side": rel.get("facing") or (rel.get("special_op") or {}).get("side"),
                    "span": (rel.get("special_op") or {}).get("span", config.DEFAULT_GATE_OPENING_SPAN),
                    "kind": kind,
                })
                continue
            attach_ops.append({
                "label": intent.label,
                "kind": kind,
                "target_group": rel.get("target"),
                "socket": rel.get("socket"),
                "near": rel.get("near"),
                "count": int(emit.get("count", intent.count)),
            })

        elif placement_mode == "path":
            obj["placement_mode"] = "path"
            obj["from"] = rel.get("target") or anchor_label
            obj["target_ref"] = rel.get("target") or anchor_label
            obj["heading"] = rel.get("facing") or "south"
            obj["steps"] = int(emit.get("length", config.DEFAULT_LINE_LENGTH))

        elif placement_mode == "follow":
            obj["placement_mode"] = "follow"
            obj["target"] = rel.get("along") or rel.get("target") or anchor_label
            obj["count"] = int(emit.get("count", intent.count))
            obj["spacing"] = int(emit.get("spacing", config.DEFAULT_FOLLOW_SPACING))
            obj["distance"] = 1

        elif placement_mode == "scatter":
            obj["placement_mode"] = "scatter"
            obj["target"] = rel.get("inside") or rel.get("target") or anchor_label
            obj["count"] = int(emit.get("count", intent.count))
            obj["radius"] = int(emit.get("radius", config.DEFAULT_RECT_FILL_SIZE[0] // 2))

        else:
            obj["placement_mode"] = "scatter"
            obj["target"] = rel.get("target") or anchor_label
            obj["count"] = int(emit.get("count", intent.count))
            obj["radius"] = int(emit.get("radius", config.DEFAULT_RECT_FILL_SIZE[0] // 2))
            warnings.append(f"{intent.label}: unsupported placement_mode '{placement_mode}' fell back to scatter")

        objects.append(obj)

    return {
        "anchor": {"type": anchor_type, "label": anchor_label},
        "ma": None,
        "objects": objects,
        "warnings": warnings,
        "layout_special_ops": special_ops,
        "layout_attach_ops": attach_ops,
        "layout_host_topology": host_topology,
        "layout_hosts_to_emit": hosts_to_emit,
        "layout_fixed_centers": fixed_centers,
    }


def compile_layout_dsl_to_legacy_spec(text: str, config: LayoutConfig = DEFAULT_CONFIG) -> dict:
    return compile_emitter_intents_to_legacy_spec(compile_layout_dsl(text, config=config), config=config)

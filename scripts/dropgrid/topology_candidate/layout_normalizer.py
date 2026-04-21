from __future__ import annotations

import shlex
from typing import Iterable

from .layout_schema import LayoutObject, NormalizedObject
from .layout_config import LayoutConfig, DEFAULT_CONFIG

KINDS = {
    "wall","fence","hedge","gate","door","tower","statue","fountain","shrine","plinth",
    "house","tent","stall","table","bed","shelf","bench","chair","road","bridge","dock",
    "rubble","crate","barrel","torch","banner","tree","log","rock",
}
ROLES = {"barrier","boundary","gate_opening","gate_frame","approach","occupant","host","marker"}
MODES = {"scatter","cluster","line","follow","rect_perimeter","rect_fill","circle_perimeter","circle_fill","attach","center"}
SOCKETS = {"face","edge","opening","corner","center","top","end"}
ALIGNS = {"align_parallel","align_perpendicular","face_toward","face_away"}
TRAITS = {"continuous","broken","formal","rough","defensive","dense","sparse"}
IMPORTANCE = {"primary","secondary","background"}
CARDINALS = {"north","south","east","west"}

KIND_SYNONYMS = {
    "rampart":"wall","palisade":"fence","doorway":"gate","hut":"house","path":"road","street":"road","desk":"table","base":"plinth",
}
ROLE_SYNONYMS = {"blocker":"barrier","enclosure":"boundary","partition":"boundary","entry_path":"approach"}
MODE_SYNONYMS = {"ring":"circle_perimeter","circle":"circle_perimeter","trace":"follow","snap":"attach"}
SOCKET_SYNONYMS = {"gap":"opening","front_face":"face"}

INFERRED_ROLES = {
    "wall":["barrier"],
    "fence":["barrier"],
    "hedge":["barrier"],
    "gate":["gate_frame"],
    "door":["gate_frame"],
    "road":["approach"],
    "bridge":["approach"],
    "dock":["approach"],
    "chair":["occupant"],
    "bench":["occupant"],
    "bed":["occupant"],
    "house":["occupant"],
    "tent":["occupant"],
    "stall":["occupant"],
}

FALLBACK_MODES = {
    "wall":"line","fence":"line","hedge":"line",
    "gate":"attach","door":"attach","torch":"attach","banner":"attach",
    "road":"follow","bridge":"follow","dock":"follow",
    "house":"cluster","tent":"cluster","stall":"cluster",
    "table":"center","bed":"center","shelf":"center","statue":"center","fountain":"center","shrine":"center","plinth":"center",
    "rubble":"scatter","crate":"scatter","barrel":"scatter","tree":"scatter","log":"scatter","rock":"scatter",
    "bench":"attach","chair":"attach",
}

CENTER_BIASED_KINDS = {"tower","statue","fountain","shrine","plinth","table"}

SOCKET_EXPOSURE = {
    "wall":{"face","edge","corner","opening","end"},
    "fence":{"face","edge","corner","opening","end"},
    "hedge":{"face","edge","corner","opening","end"},
    "table":{"top","edge","center","corner"},
    "plinth":{"top","edge","center"},
    "bed":{"edge","center"},
    "shelf":{"top","edge"},
    "house":{"face","edge"},
    "tower":{"face","edge"},
    "road":{"edge","end","center"},
    "bridge":{"edge","end","center"},
    "dock":{"edge","end","center"},
    "statue":{"center","edge"},
    "fountain":{"center","edge"},
    "shrine":{"face","center","edge"},
}

ZONE_PRODUCING_MODES = {"rect_perimeter","circle_perimeter","rect_fill","circle_fill"}
AABB_ZONE_KINDS = {"table","bed","shelf","house","tower","statue","fountain","shrine","plinth"}

class LayoutSpecError(ValueError):
    def __init__(self, reason: str, target: str, suggestion: str):
        super().__init__(reason)
        self.reason = reason
        self.target = target
        self.suggestion = suggestion

    def as_text(self) -> str:
        return f"ERROR: {self.reason}.\nTARGET: {self.target}\nSUGGESTION: {self.suggestion}"


def _canon(token: str | None, table: dict[str,str], allowed: set[str], field: str, target: str) -> str | None:
    if token is None:
        return None
    token = table.get(token, token)
    if token not in allowed:
        raise LayoutSpecError(f"unknown {field} '{token}'", target, f"use a V1.2 canonical {field} or add a synonym before compile")
    return token


def parse_layout_dsl(text: str) -> list[LayoutObject]:
    objs: list[LayoutObject] = []
    current: dict | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        toks = shlex.split(stripped)
        if toks[0] == "object":
            if current:
                objs.append(LayoutObject(**current))
            if len(toks) < 2:
                raise ValueError("object line missing kind")
            current = {"kind": toks[1], "label": None}
            continue
        if current is None:
            raise ValueError(f"field outside object block: {stripped}")
        key = toks[0]
        values = toks[1:]
        if key in {"label","mode","target","inside","outside","around","along","near","facing","socket","align","importance"}:
            current[key] = values[0] if values else None
        elif key == "count":
            current[key] = int(values[0])
        elif key in {"roles","traits"}:
            current[key] = list(values)
        else:
            raise ValueError(f"unknown field {key}")
    if current:
        objs.append(LayoutObject(**current))
    for obj in objs:
        if not obj.label:
            raise ValueError(f"object {obj.kind} missing label")
    return objs


def normalize_objects(objects: Iterable[LayoutObject], config: LayoutConfig = DEFAULT_CONFIG) -> list[NormalizedObject]:
    draft = list(objects)
    labels = {o.label: o for o in draft}
    out: list[NormalizedObject] = []

    for obj in draft:
        kind = _canon(obj.kind, KIND_SYNONYMS, KINDS, "kind", obj.label)
        roles = [_canon(r, ROLE_SYNONYMS, ROLES, "role", obj.label) for r in (obj.roles or [])]
        mode = _canon(obj.mode, MODE_SYNONYMS, MODES, "mode", obj.label) if obj.mode else None
        socket = _canon(obj.socket, SOCKET_SYNONYMS, SOCKETS, "socket", obj.label) if obj.socket else None
        align = _canon(obj.align, {}, ALIGNS, "align", obj.label) if obj.align else None
        importance = obj.importance or "secondary"
        if importance not in IMPORTANCE:
            raise LayoutSpecError(f"unknown importance '{importance}'", obj.label, "use primary, secondary, or background")
        if obj.facing and obj.facing not in CARDINALS:
            raise LayoutSpecError("facing must be one of north, south, east, or west in V1.2", obj.label, "use a cardinal facing, or use align with a reference object if relative orientation is needed")
        traits = list(obj.traits or [])
        for t in traits:
            if t not in TRAITS:
                raise LayoutSpecError(f"unknown trait '{t}'", obj.label, "use a V1.2 canonical trait")
        if "dense" in traits and "sparse" in traits:
            raise LayoutSpecError("conflicting traits dense and sparse", obj.label, "choose either dense or sparse")
        if mode in {"box","travel"}:
            raise LayoutSpecError(f"unsupported mode '{mode}'", obj.label, "use rect_perimeter / rect_fill or follow")
        inferred_roles = [r for r in INFERRED_ROLES.get(kind, []) if r not in roles]
        roles.extend(inferred_roles)
        host_ref = obj.target or obj.inside or obj.around or obj.along or obj.near
        target_kind = labels[obj.target].kind if obj.target and obj.target in labels else None
        zone_kind = labels[obj.inside].kind if obj.inside and obj.inside in labels else None

        if mode is None:
            if socket:
                mode = "attach"
            elif obj.along:
                mode = "follow"
            elif obj.around:
                mode = "circle_perimeter" if (("barrier" in roles) or ("boundary" in roles) or kind in {"wall","fence","hedge"}) else "circle_fill"
            elif obj.inside:
                zone_obj = labels.get(obj.inside)
                zone_mode = zone_obj.mode if zone_obj else None
                zone_mode = MODE_SYNONYMS.get(zone_mode, zone_mode) if zone_mode else None
                mode = "rect_fill" if zone_mode in {None, "rect_perimeter", "rect_fill"} else "circle_fill"
            else:
                mode = FALLBACK_MODES[kind]

        if obj.inside and mode in {"rect_fill","circle_fill"} and (obj.count or 1) == 1 and obj.mode is None and kind in CENTER_BIASED_KINDS:
            mode = "center"

        # align reference
        align_ref = None
        if align in {"face_toward","face_away"}:
            for candidate in [obj.target, obj.near, obj.along, obj.around, obj.inside, obj.outside]:
                if candidate:
                    align_ref = candidate
                    break
            if not align_ref:
                raise LayoutSpecError(f"align value '{align}' requires a resolvable reference", obj.label, "add target or near to provide an orientation reference")

        if mode == "attach":
            if not obj.target:
                raise LayoutSpecError("attach mode requires a target host", obj.label, "add target <label> for the host object")
            host_obj = labels.get(obj.target)
            if host_obj is None:
                raise LayoutSpecError("attach target could not be resolved", obj.target, "declare the host label before attaching to it")
            host_kind = KIND_SYNONYMS.get(host_obj.kind, host_obj.kind)
            target_kind = host_kind
            if socket is None:
                # role preferences
                if "gate_opening" in roles:
                    socket = "opening"
                elif "gate_frame" in roles:
                    socket = "opening" if "opening" in SOCKET_EXPOSURE.get(host_kind, set()) else "face"
                elif "marker" in roles:
                    socket = "face" if "face" in SOCKET_EXPOSURE.get(host_kind, set()) else "edge"
                elif "occupant" in roles:
                    socket = "edge" if "edge" in SOCKET_EXPOSURE.get(host_kind, set()) else "center"
            if host_kind not in SOCKET_EXPOSURE or socket not in SOCKET_EXPOSURE[host_kind]:
                raise LayoutSpecError(f"socket '{socket}' is illegal for target kind '{host_kind}'", obj.target, "use align instead of attach, or target a host that exposes the requested socket")
            if "gate_opening" in roles and host_kind not in {"wall","fence","hedge"}:
                raise LayoutSpecError("gate_opening requires a barrier or boundary host with an opening-capable perimeter", obj.target, "target a wall, fence, or hedge perimeter host")

        if obj.inside:
            zone_obj = labels.get(obj.inside)
            if zone_obj is None:
                raise LayoutSpecError("inside target could not be resolved", obj.inside, "declare the zone host before referencing it")
            zkind = KIND_SYNONYMS.get(zone_obj.kind, zone_obj.kind)
            zmode = MODE_SYNONYMS.get(zone_obj.mode, zone_obj.mode) if zone_obj.mode else None
            if not (zmode in ZONE_PRODUCING_MODES or zkind in AABB_ZONE_KINDS):
                raise LayoutSpecError("inside requires a valid zone-producing host or usable AABB zone", obj.inside, "use attach with socket 'edge' or use center if appropriate")

        out.append(NormalizedObject(
            kind=kind, label=obj.label, count=obj.count or 1, roles=roles, mode=mode,
            target=obj.target, inside=obj.inside, outside=obj.outside, around=obj.around, along=obj.along, near=obj.near,
            facing=obj.facing, socket=socket, align=align, traits=traits, importance=importance, host_ref=host_ref,
            align_ref=align_ref, target_kind=target_kind, zone_kind=zone_kind, inferred_roles=inferred_roles
        ))
    return out

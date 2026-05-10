from __future__ import annotations
import shlex

def parse_object_scene(text: str) -> dict:
    anchor = None
    ma = None
    objects = []
    warnings = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        toks = shlex.split(line)
        if not toks:
            continue
        if toks[0] == "anchor":
            anchor = {"type": toks[1], "label": toks[2] if len(toks) > 2 else toks[1]}
        elif toks[0] == "ma":
            # supported:
            # ma radius 4
            # ma hard radius 4
            # ma soft radius 4
            # ma reserve radius 4
            if len(toks) >= 3 and toks[1] in {"hard", "soft", "reserve"} and "radius" in toks:
                ma = {"mode": toks[1], "radius": int(float(toks[toks.index("radius") + 1]))}
            elif len(toks) >= 3 and toks[1] == "radius":
                ma = {"mode": "hard", "radius": int(float(toks[2]))}
        elif toks[0] == "object":
            obj = {"type": toks[1]}
            i = 2
            while i < len(toks):
                k = toks[i]
                needs_value = k in {
                    "label", "target", "from", "heading", "shape", "side",
                    "symbol", "to", "near",
                    "count", "steps", "clusters", "spacing", "distance", "radius",
                    "spread", "arc", "wobble",
                }
                if needs_value and i + 1 >= len(toks):
                    # Keyword at end of line with no value — skip and warn
                    warnings.append(
                        f"object {obj['type']}: keyword '{k}' has no value, ignored"
                    )
                    i += 1
                    continue
                if k in {"label", "target", "from", "heading", "shape", "side", "symbol", "to", "near"}:
                    obj[k] = toks[i + 1]
                    i += 2
                elif k in {"count", "steps", "clusters", "spacing", "distance", "radius"}:
                    obj[k] = int(float(toks[i + 1]))
                    i += 2
                elif k in {"spread", "arc", "wobble"}:
                    obj[k] = float(toks[i + 1])
                    i += 2
                else:
                    i += 1
            # If both count and steps are given, steps is only a path alias — count takes precedence.
            # Warn if they differ so the user knows which is being used.
            if "count" in obj and "steps" in obj and obj["count"] != obj["steps"]:
                warnings.append(
                    f"object {obj['type']}: both count={obj['count']} and steps={obj['steps']} given; "
                    f"count takes precedence for non-path modes, steps for path mode"
                )
            # Warn if heading is given without from (path mode won't trigger)
            if "heading" in obj and "from" not in obj:
                warnings.append(
                    f"object {obj['type']}: 'heading' given without 'from'; "
                    f"path mode requires both — add 'from <label>' to activate path placement"
                )
            objects.append(obj)
    return {"anchor": anchor, "ma": ma, "objects": objects, "warnings": warnings}

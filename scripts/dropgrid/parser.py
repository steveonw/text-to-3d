from __future__ import annotations
import shlex

def parse_object_scene(text: str) -> dict:
    anchor = None
    ma = None
    objects = []
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
                if k in {"label", "target", "from", "heading", "shape", "side", "symbol"}:
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
            objects.append(obj)
    return {"anchor": anchor, "ma": ma, "objects": objects}

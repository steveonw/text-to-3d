# Full-Loop Worked Example — Shrine Clearing

This trace shows the complete pipeline for a small outdoor shrine: one campfire
altar, a dirt path heading south, lanterns flanking the path, and trees ringing
the clearing.

---

## 1. One-sentence scene

> "A campfire altar at the center of a forest clearing, with a dirt path leading
> south from it, lanterns along the path, and trees around the edge."

---

## 2. Decompose to needs

```
NEEDS:
1. campfire  — single anchor, the focal point. 1 piece.
2. road      — path heading south from the altar. ~10 pieces.
3. lantern   — flanking the path, alternating sides. ~4 pieces.
4. tree      — ring around the clearing, clustered. ~8 pieces.

Count: 23 pieces. All placement handled by solver.
```

---

## 3. Write the DSL

```
anchor campfire altar
ma hard radius 3

object road label path count 10 from altar heading south steps 10 wobble 0.1
object lantern label lanterns count 4 target road side any distance 1 spacing 2
object tree label forest count 8 shape circle radius 7 clusters 4 spread 1
```

---

## 4. Solver output

Run: `solve_object_scene(DSL, seed=42)`

### ASCII layout

```
00 ························
01 ························
...
05 ·············tt·········
...
09 ··············░·········
10 ············░░░░░·······
11 ············░░░░░····t··
12 ·······t···░░░*░░░···t··  ← campfire at (14,12)
13 ·······t····░░░░░·······
14 ············░░░░░·······
15 ··············░·········
16 ··············=·L·······  ← road + first lantern
17 ··············=·········
18 ··············=·L·······
19 ··············=tt·······
20 ··············=·L·······
21 ··············=·········
22 ··············=·L·······
...
Legend: *=campfire  ==road  L=lantern  t=tree  ░=MA
```

### Piece list

| id | type     | label       | pos     | rot | family |
|----|----------|-------------|---------|-----|--------|
| 1  | campfire | altar       | (14,12) | 0   | anchor |
| 2  | road     | path_0      | (14,16) | 1   | path   |
| …  | road     | path_1–9    | …       | 1   | path   |
| 11 | road     | path_9      | (14,25) | 1   | path   |
| 12 | lantern  | lanterns_0  | (16,16) | 0   | prop   |
| 13 | lantern  | lanterns_1  | (16,18) | 0   | prop   |
| 14 | lantern  | lanterns_2  | (16,20) | 0   | prop   |
| 15 | lantern  | lanterns_3  | (16,22) | 0   | prop   |
| 16 | tree     | forest_0    | (15,19) | 1   | flora  |
| 17 | tree     | forest_1    | (7,12)  | 0   | flora  |
| …  | tree     | forest_2–7  | …       | …   | flora  |
| 23 | tree     | forest_7    | (21,11) | 0   | flora  |

---

## 5. Per-piece context

`export_all_contexts(result)` produces one packet per piece. Selected examples:

### Piece 1 — campfire (anchor, interior)

```json
{
  "self": { "id": 1, "type": "campfire", "position": {"x": 14, "z": 12}, "facing": "N" },
  "interior": true,
  "on_cluster_edge": false,
  "near_path": false,
  "path_direction": null,
  "outward_direction": "N",
  "neighbors": [
    { "type": "road",    "direction": "S",  "distance": 4.0 },
    { "type": "lantern", "direction": "SE", "distance": 4.47 },
    { "type": "road",    "direction": "S",  "distance": 5.0 }
  ]
}
```

**Reading:** Anchor piece at scene center, interior, no path nearby. The nearest
things are the road going south and a lantern to the SE. Author this as the
focal object — it should read clearly from all sides.

### Piece 12 — lantern (path-flanking, interior)

```json
{
  "self": { "id": 12, "type": "lantern", "position": {"x": 16, "z": 16}, "facing": "N" },
  "interior": true,
  "on_cluster_edge": false,
  "near_path": true,
  "path_direction": "W",
  "outward_direction": "NE",
  "neighbors": [
    { "type": "road",    "direction": "W",  "distance": 2.0 },
    { "type": "lantern", "direction": "S",  "distance": 2.0 },
    { "type": "road",    "direction": "SW", "distance": 2.24 }
  ]
}
```

**Reading:** Right beside the path (path is 2 cells to the west). Interior
position — enclosed by path and other lanterns. The lantern should lean or face
toward the path. Its job is wayfinding.

### Piece 17 — tree (edge, no path)

```json
{
  "self": { "id": 17, "type": "tree", "position": {"x": 7, "z": 12}, "facing": "N" },
  "interior": false,
  "on_cluster_edge": true,
  "near_path": false,
  "path_direction": null,
  "outward_direction": "NW",
  "neighbors": [
    { "type": "tree",     "direction": "S",  "distance": 1.0 },
    { "type": "campfire", "direction": "E",  "distance": 7.0 },
    { "type": "tree",     "direction": "SE", "distance": 7.07 }
  ]
}
```

**Reading:** Edge of the cluster, facing outward to the NW. No path nearby.
This tree is on the perimeter — author it leaning slightly outward, maybe a bit
weather-beaten. It defines the boundary of the clearing.

---

## 6. Geometry authoring

For each piece, produce a geometry packet. The context above informs the
authoring choices; no two pieces need to be identical.

### Piece 1 — campfire

Focal piece at the center. Low, spreading, warm glow.

```json
{
  "piece_id": 1,
  "primitives": [
    {
      "shape": "cylinder",
      "dimensions": [0.45, 0.45, 0.08],
      "position": [0.0, 0.04, 0.0],
      "rotation": [0.0, 0.0, 0.0],
      "material": { "color": "#3a2a1a", "roughness": 0.9, "metalness": 0.0 }
    },
    {
      "shape": "cone",
      "dimensions": [0.3, 0.5],
      "position": [-0.05, 0.3, 0.05],
      "rotation": [5.0, 20.0, 0.0],
      "material": { "color": "#5c3d1e", "roughness": 0.9, "metalness": 0.0 }
    },
    {
      "shape": "cone",
      "dimensions": [0.25, 0.45],
      "position": [0.06, 0.28, -0.04],
      "rotation": [-3.0, 60.0, 0.0],
      "material": { "color": "#4a3018", "roughness": 0.9, "metalness": 0.0 }
    },
    {
      "shape": "sphere",
      "dimensions": [0.18],
      "position": [0.0, 0.22, 0.0],
      "rotation": [0.0, 0.0, 0.0],
      "material": {
        "color": "#ff6622",
        "roughness": 0.5,
        "metalness": 0.0,
        "emissive": "#ff4400",
        "emissive_intensity": 1.2
      }
    }
  ]
}
```

*Authoring note: Stone ring base, two crossed log cones with slight variation in
angle and size, glowing ember sphere at the center. The logs are not symmetric —
one tilts north-east, the other south-east. Focal piece, so make it readable.*

### Piece 12 — lantern (path-flanking)

Path is to the west. Lean toward it. Post + cage + glow.

```json
{
  "piece_id": 12,
  "primitives": [
    {
      "shape": "cylinder",
      "dimensions": [0.04, 0.04, 1.4],
      "position": [0.0, 0.7, 0.0],
      "rotation": [0.0, 0.0, -3.0],
      "material": { "color": "#3a3a3e", "roughness": 0.6, "metalness": 0.5 }
    },
    {
      "shape": "box",
      "dimensions": [0.28, 0.04, 0.28],
      "position": [0.0, 1.4, 0.0],
      "rotation": [0.0, 0.0, 0.0],
      "material": { "color": "#2a2a2e", "roughness": 0.5, "metalness": 0.6 }
    },
    {
      "shape": "box",
      "dimensions": [0.2, 0.32, 0.2],
      "position": [0.0, 1.56, 0.0],
      "rotation": [0.0, 0.0, 0.0],
      "material": {
        "color": "#ffdd88",
        "roughness": 0.3,
        "metalness": 0.0,
        "emissive": "#ffbb44",
        "emissive_intensity": 0.9
      }
    },
    {
      "shape": "box",
      "dimensions": [0.28, 0.04, 0.28],
      "position": [0.0, 1.72, 0.0],
      "rotation": [0.0, 0.0, 0.0],
      "material": { "color": "#2a2a2e", "roughness": 0.5, "metalness": 0.6 }
    }
  ]
}
```

*Authoring note: Iron post with slight westward lean (toward path), flat cap
and base plate, glowing box lantern in the middle. This is the first lantern —
it's the tallest and leans most directly toward the path. Path-flanking pieces
earn their context.*

### Piece 17 — tree (edge, NW outward)

Perimeter tree, leans outward to the NW. Scraggier than a sheltered tree.

```json
{
  "piece_id": 17,
  "primitives": [
    {
      "shape": "cylinder",
      "dimensions": [0.14, 0.18, 1.1],
      "position": [0.0, 0.55, 0.0],
      "rotation": [0.0, 0.0, 4.0],
      "material": { "color": "#4a3218", "roughness": 0.9, "metalness": 0.0 }
    },
    {
      "shape": "cone",
      "dimensions": [0.5, 1.1],
      "position": [-0.06, 1.65, 0.06],
      "rotation": [0.0, 0.0, 5.0],
      "material": { "color": "#2a5022", "roughness": 0.85, "metalness": 0.0 }
    },
    {
      "shape": "cone",
      "dimensions": [0.35, 0.75],
      "position": [-0.09, 2.3, 0.08],
      "rotation": [0.0, 0.0, 6.0],
      "material": { "color": "#1e4019", "roughness": 0.85, "metalness": 0.0 }
    }
  ]
}
```

*Authoring note: Slightly tapered trunk, two-tiered canopy (wider lower cone,
narrower upper). Both cones and trunk lean NW (outward_direction). The upper
canopy is darker — it's the outer layer of the forest. Perimeter trees earn
their edge position.*

---

## 7. Validation

```python
from authoring.geometry_receiver import receive_all

packets = receive_all([packet_1, packet_12, packet_17, ...])
# Returns {1: ..., 12: ..., 17: ...} — raises GeometryError on any violation
```

Optional: spot-check with `braille_view` or `path_walk` if spacing is uncertain.

---

## 8. Assemble the HTML

```python
from dropgrid.api import solve_object_scene
from authoring.context_exporter import export_all_contexts
from authoring.geometry_receiver import receive_all
from scripts.scaffold.scaffold_v4_walkmode import generate_scene_html

result = solve_object_scene(DSL, seed=42)
packets = receive_all([...all authored packets...])
html = generate_scene_html(result, packets, title="Shrine Clearing")

with open("shrine_clearing.html", "w") as f:
    f.write(html)
```

Open `shrine_clearing.html` in a browser. Orbit mode by default; press **F** to
walk through the scene.

---

## What this loop demonstrates

| Step | Tool | What it contributes |
|------|------|---------------------|
| DSL → solver | `solve_object_scene` | Positions all 23 pieces without Claude tracking coordinates |
| Context export | `export_all_contexts` | Tells Claude what's near each piece, whether it's edge/interior, path-adjacent |
| Geometry authoring | Claude + schema | One packet per piece; each one a small contextual decision |
| Validation | `receive_all` | Schema errors caught before they reach the renderer |
| HTML generation | `generate_scene_html` | Packets + positions → walkable Three.js scene |

The campfire at the center reads differently from a lantern beside the path,
which reads differently from a perimeter tree leaning outward. That difference
comes from context, not from separate templates. That is the whole point.

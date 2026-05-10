# Authoring Guide — Context-Aware Geometry

How to author geometry packets that look handcrafted rather than stamped.
Read `references/philosophy.md` first if you haven't.

---

## 0. What this guide does — and doesn't — fix

This guide covers **per-piece geometry authoring**: how to read context and produce
primitives that look handcrafted rather than stamped.

It does **not** fix:

| Problem | Where it's fixed |
|---|---|
| Scene feels unlit / flat / dim | Scaffold defaults (lighting, hemisphere light) |
| Pieces float with no ground | Scaffold `ground_color` parameter |
| Path goes nowhere / dead-ends | DSL — use different path endpoint or `to B` |
| Outlier pieces scattered far from the rest | DSL — tighten radius or anchor to a piece |
| Two pieces of the same type look identical | This guide — read section 4 |
| Piece silhouette wrong (cone reads as antenna) | This guide — see section 3 primitive vocabulary |

If your scene still feels off after following this guide, the problem is almost
certainly in the scaffold or DSL, not in authoring.  Read the ASCII before
authoring (SKILL.md step 4) — two of the most common quality failures are
visible there before any geometry is written.

---

## The one-sentence job

For each placed piece, produce a geometry packet — a list of Three.js-style
primitives in the piece's local coordinate space — that looks right *for that
specific piece in that specific position*.

The solver handles placement. Your entire job is appearance, one piece at a time.

---

## 1. Reading a context packet

Every piece arrives with a context packet from `export_piece_context()`. Before
writing a single primitive, read it.

```json
{
  "self":            { "type": "tree", "position": {"x": 7, "z": 12}, "facing": "N" },
  "interior":        false,
  "on_cluster_edge": true,
  "in_corner":       false,
  "near_path":       false,
  "path_direction":  null,
  "outward_direction": "NW",
  "neighbors": [
    { "type": "tree",     "direction": "S",  "distance": 1.0 },
    { "type": "campfire", "direction": "E",  "distance": 7.0 }
  ]
}
```

**What to notice:**

| Field | What it tells you |
|---|---|
| `interior` / `on_cluster_edge` | Is this piece enclosed by others or on the perimeter? |
| `in_corner` | Does it sit at a bend where two open directions meet? |
| `near_path` + `path_direction` | Is a road/path nearby, and which way? |
| `outward_direction` | Which way is "away from the scene center"? |
| `neighbors[0]` | The closest piece — what it is and where it sits |
| `facing` | Which compass direction the piece's front faces (from `rot`) |

Pick **one or two** of these signals and let them shape your authoring choice.
You don't need to react to every field.

---

## 2. Coordinate conventions

- **y = 0 is the floor.** All geometry sits on or above y = 0.
- **y-up.** Positive y is upward.
- **Positions are local to the piece's grid anchor.** The piece's grid cell
  center is at (0, 0, 0) in local space. Write positions relative to that.
- **Rotations are in degrees**, applied as Euler x/y/z.
- **One grid cell ≈ 1 scene unit.** A tall tree is ~2 units high. A person is
  ~1.8 units. A wall panel is ~0.1 units thick.

**Stacking rule** (the most common source of geometry errors):

Three.js centers geometries at their origin. A box of height `h` needs
`position.y = h / 2` to sit on the floor:

```json
{ "shape": "box", "dimensions": [0.5, 1.0, 0.5], "position": [0, 0.5, 0] }
```

For a stack — trunk at floor, foliage above it:
```
trunk:   dimensions [0.15, 0.9, 0.15], position [0, 0.45, 0]
foliage: dimensions [0.55, 1.2, 0.55], position [0, 0.9 + 0.6, 0]  (trunk top + half foliage)
       = position [0, 1.5, 0]
```

---

## 3. Primitive vocabulary

Five shapes. Use them in combination.

| Shape | Dimensions | Good for |
|---|---|---|
| `box` | `[width, height, depth]` | trunks, posts, walls, crates, lantern bodies, steps |
| `cylinder` | `[radius_top, radius_bottom, height]` | posts, columns, barrels, tree trunks |
| `cone` | `[radius, height]` | tree tops, hat brims, spire tips, flame shapes |
| `sphere` | `[radius]` | fire glow, round fruit, cannonballs, lamp globes |
| `plane` | `[width, height]` | thin panels, signs, fabric, ground patches |

**Tapering:** cylinders can taper by setting different radii — `[0.1, 0.15, 1.0]`
makes a trunk wider at the base, which looks more natural than a pure cylinder.

**Composition patterns** (heuristics, not templates — adapt each time):

```
Tree:       cylinder (trunk) + cone (foliage) [+ smaller cone above]
Lantern:    cylinder (post) + box (cage) + sphere/box (glow)
Fence post: thin box (post) + thin boxes (rails between posts)
Campfire:   flat cylinder (stone ring) + 2–3 cones (logs) + sphere (glow)
Bush:       sphere or wide low cone
Rock:       box with slight random rotation
Sign:       thin box (post) + plane (board)
Person:     cylinder (body) + sphere (head)
```

None of these are recipes. They're starting points. Every authoring pass
should produce a slightly different version.

---

## 4. Silhouette recipes — common types

These are starting points, not templates. Each scene is different — adjust proportions,
lean, and color every time. The goal is to see *what reads correctly* vs what reads wrong.

### Tent

**Wrong:** a tall narrow cone reads as an antenna or Christmas tree.  
**Right:** a wide low cone (radius ≥ 0.7 × height) with a separate entrance box.

```
Wrong       Right
  /\         ___
 /  \       /   \
/    \    /______\  ← wide cone
              []     ← entrance (front box)
```

```python
# tent body — wide and squat
{"shape": "cone",       "dimensions": [0.75, 1.0],       "position": [0.0, 0.5, 0.0]}
# entrance — small box at the front edge (z+ = "front")
{"shape": "box",        "dimensions": [0.28, 0.45, 0.12], "position": [0.0, 0.22, 0.42]}
# optional ridge pole
{"shape": "cylinder",   "dimensions": [0.03, 0.03, 1.2],  "position": [0.0, 1.0, 0.0],
                        "rotation": [0.0, 0.0, 90.0]}
```

Contextual variation: edge tents tilt the cone 4–6° toward `outward_direction`.
Interior tents have the entrance facing inward (flip z sign). Weathered tents
use higher roughness (0.9+) and muted browns.

---

### Barrel

**Wrong:** a very tall narrow cylinder reads as a pipe or post.  
**Right:** a fat short cylinder, radius close to half the height.

```python
# barrel — roughly as wide as it is tall
{"shape": "cylinder",  "dimensions": [0.28, 0.32, 0.6],  "position": [0.0, 0.3, 0.0]}
# optional lid
{"shape": "cylinder",  "dimensions": [0.30, 0.30, 0.05], "position": [0.0, 0.62, 0.0]}
```

Taper options: `[0.26, 0.30, 0.6]` (bulged in the middle — use for wooden barrel feel).
Standing: y-axis. Lying on side: rotate 90° on z and shift y down to `radius`.

---

### Log

**Wrong:** a vertical cylinder reads as a post.  
**Right:** a horizontal cylinder — rotate 90° on the z-axis, y position = radius.

```python
# log lying flat, oriented E-W
{"shape": "cylinder",  "dimensions": [0.14, 0.14, 0.85], "position": [0.0, 0.14, 0.0],
                       "rotation": [0.0, 0.0, 90.0]}
```

For logs around a campfire, vary the z-rotation (70–90°) and x-offset so they
lean slightly inward. A log at `near_path=true` can be oriented along the
`path_direction` axis.

---

### Tree

**Wrong:** identical trunk + cone for every tree — reads as stamped.  
**Right:** vary trunk taper, canopy width, lean, and whether there's a second layer.

```python
# Forest interior tree — vertical, layered canopy
{"shape": "cylinder",  "dimensions": [0.10, 0.16, 0.85], "position": [0.0, 0.42, 0.0]}
{"shape": "cone",      "dimensions": [0.52, 1.3],         "position": [0.0, 1.5, 0.0]}
{"shape": "cone",      "dimensions": [0.36, 0.9],         "position": [0.0, 2.3, 0.0]}

# Edge tree leaning outward (outward_direction="W") — tilt trunk, offset canopy
{"shape": "cylinder",  "dimensions": [0.12, 0.18, 0.9],  "position": [-0.08, 0.45, 0.0],
                       "rotation": [0.0, 0.0, -5.0]}
{"shape": "cone",      "dimensions": [0.6, 1.4],          "position": [-0.15, 1.5, 0.0]}

# Lone tree at corner — wide spreading canopy
{"shape": "cylinder",  "dimensions": [0.14, 0.14, 0.7],  "position": [0.0, 0.35, 0.0]}
{"shape": "cone",      "dimensions": [0.7, 1.1],          "position": [0.0, 1.25, 0.0]}
```

Pick one of these families and vary the numbers — don't copy the exact values.

---

### Fence post with rails

**Wrong:** a tall thin box — looks like a blade, no visual weight.  
**Right:** a square-section post with two horizontal rails connecting to neighbors.

```python
# post
{"shape": "box",  "dimensions": [0.1, 0.9, 0.1],  "position": [0.0, 0.45, 0.0]}
# rail high (connecting to neighbors in the x direction)
{"shape": "box",  "dimensions": [0.9, 0.07, 0.06], "position": [0.0, 0.72, 0.0]}
# rail low
{"shape": "box",  "dimensions": [0.9, 0.07, 0.06], "position": [0.0, 0.38, 0.0]}
```

For fences running N-S, swap the rail dimensions: `[0.06, 0.07, 0.9]`.
Context: a fence piece `near_path=true` can lean slightly toward the path.
A corner post (`in_corner=true`) can be a bit taller and heavier (0.13 × 0.13 cross-section).

---

### Quick height reference

| Type | Typical height | Cone/cylinder ratio |
|---|---|---|
| Barrel | 0.5–0.7 | diameter ≈ height |
| Log (lying) | 0.15–0.2 (= radius) | horizontal |
| Tent | 0.8–1.2 | base radius ≥ 0.65 × height |
| Fence post | 0.8–1.0 | 0.08–0.12 cross-section |
| Tree trunk | 0.7–1.0 | 0.10–0.20 radius |
| Tree canopy | 1.0–1.5 | 0.45–0.75 radius |

---

## 5. The craft — contextual variation

This is the part that matters. Geometry primitives are easy. Making them
*respond to context* is the skill.

### Edge vs. interior

An **edge** piece is on the perimeter of the scene. It has an open half-space
in some direction — there are no neighbors beyond it. An **interior** piece is
enclosed on all sides.

| Context | What to do |
|---|---|
| `on_cluster_edge: true` | Lean slightly outward (`outward_direction`). Rougher, more exposed. Can afford to be taller or more dramatic — it reads against empty space, not against neighbors. |
| `interior: true` | More compact. Doesn't need to stand out. Can be quieter — it's framed by surrounding pieces. Focal pieces (anchor, host) are always interior by definition. |

```
Edge tree at outward_direction="NW":
  trunk rotated 3–5° toward NW (rotation z or x)
  foliage cone position offset slightly NW

Interior tree (deep in forest):
  compact, vertical, no lean
  foliage wider — it spreads into available space
```

### Near a path

`near_path: true` means a road or path is nearby. The `path_direction` field
says which way.

| Context | What to do |
|---|---|
| Lantern near path | Face the lantern toward the path. Lean the post slightly toward it. |
| Tree near path | Trees near paths are trimmed at the base — shorter lower branches. Lean slightly away from the path (trampled side). |
| Bench near path | Rotate the bench to face the path. |
| Decorative post | Taller on the path-facing side. |

### Corner pieces

`in_corner: true` means the piece sits at a bend — two open sectors, forming
an L-shape. Think of a wall corner or a tree at the edge of a curved clearing.

Corner pieces should acknowledge both open directions. A tree in a corner can
have two foliage asymmetries, one for each gap.

### Facing / rotation

`facing` is the piece's front direction from the solver's rotation:
`N / E / S / W`. This affects which direction details should point.

A lantern with `facing: "E"` has its front to the east. If it also has
`path_direction: "W"`, the path is behind it — so the lantern should either
face the path (override with geometry lean) or light the path side with a
brighter glow.

### The neighbor list

The first neighbor is the closest piece. Use it for fine adjustments.

```
Tree with nearest neighbor = another tree at direction="S", distance=1.0:
  These two trees are close together. Make this one lean away — N or NW.
  Make it slightly taller (competing for light).

Lantern with nearest neighbor = road at direction="W", distance=2.0:
  The road is close to the west. The lantern faces the road.
```

---

## 6. Scale discipline

Your primitives must fit within the piece's footprint. Each piece occupies
one grid cell (1 × 1 in x/z). The maximum width/depth of any geometry is 0.9
units in each horizontal axis (leave ~0.05 clearance on each side).

Height has more freedom — a tall tree at 2.5 units is fine; a cathedral
spire at 6 units is fine if the scene calls for it. But keep scale consistent
within a scene: if trees are ~2 units, don't make one tree 4 units.

---

## 7. Material choices

Color, roughness, and metalness carry as much meaning as shape.

| Material type | roughness | metalness | Notes |
|---|---|---|---|
| Rough stone / earth | 0.85–0.95 | 0.0 | Default for natural objects |
| Weathered wood | 0.80–0.90 | 0.0 | Tree trunks, fence posts |
| Clean wood / furniture | 0.65–0.75 | 0.0 | Indoor wood, fresh-cut |
| Fired clay / brick | 0.75–0.85 | 0.0 | |
| Wrought iron | 0.55–0.70 | 0.3–0.5 | Lantern frames, gate hinges |
| Polished metal | 0.10–0.25 | 0.8–1.0 | Coins, blades |
| Candle / fire glow | 0.3–0.5 | 0.0 | Add `emissive` |
| Glass / crystal | 0.05–0.15 | 0.0–0.1 | Add `emissive` for lit glass |

**Emissive materials** — use for light sources only:
```json
{
  "color": "#ffdd88",
  "roughness": 0.3,
  "metalness": 0.0,
  "emissive": "#ffbb44",
  "emissive_intensity": 0.8
}
```

Colors should feel earned by context. A campfire in a gloomy scene should
glow warmer and brighter than one in bright daylight. A lantern at the far
end of a path should be slightly dimmer than one right beside the viewer.

---

## 8. Anti-patterns

### Stamping

Authoring piece #3 with the same primitive list as piece #1, just rotated,
is stamping. Even if the rotation changes, it reads as a template.

**Telltale:** You wrote a function or variable called `make_tree()` or
`tree_primitives`. That's a template in disguise.

**Fix:** For each tree, look at its context packet and make a concrete decision.
"This one leans west because `outward_direction` is W and it's on the edge."
Different decision → different geometry.

### Ignoring context

Producing geometry without reading the context packet. "It's a tree, so:
trunk + cone, done." This produces a scene where every tree looks identical
regardless of position.

**Fix:** Read the packet. Pick at least one field. Let it change something.

### Over-varying

Each piece wildly different from every other — a tree that's a single
sphere, a tree that's 12 tiny boxes, a tree that's a plane. This produces
noise, not craft.

**Fix:** Stay within the vocabulary of the type. Trees are trees — they
vary in proportion, lean, density, and color. They don't vary in kind.

### Ignoring the footprint

Placing primitives at position [3, 0, 0] when the piece is 1×1. This bleeds
geometry into neighboring cells.

**Fix:** Keep x and z positions within ±0.45 of origin.

### Floating geometry

Setting a box's position.y = 0 when it has height 1.0 — the box is half
underground.

**Fix:** position.y = height / 2 for floor-level pieces. Stack from there.

---

## 9. When reuse is acceptable

Not every piece benefits from unique geometry. Use judgement.

**Author each piece distinctly:**
- Trees, bushes, rocks, props — visible individuality matters
- Lanterns, torches, fence posts — small variation in lean/height adds life
- Any focal or anchor piece — it's the scene center; it deserves care

**Reuse is acceptable:**
- Tiled floor cells, paving stones, identical bricks in a wall
- Road segments (they're meant to look uniform)
- Underground or invisible geometry

The test: *would a viewer notice if these two pieces were swapped?* If yes,
author them distinctly. If no, it's okay to repeat.

---

## 10. Quick reference — authoring checklist

Before submitting a geometry packet for a piece:

- [ ] Read the context packet. Identified at least one signal to react to.
- [ ] All `position.y` values are `height/2` above the intended floor level.
- [ ] Geometry footprint stays within ±0.45 in x and z.
- [ ] Colors feel right for the piece type and scene mood.
- [ ] This piece looks different from the last piece of the same type.
- [ ] No function definitions, no reused variable names across pieces.

---

## See also

- `references/cross_piece_narrative.md` — once per-piece silhouettes are solid, add the kettles, ropes, and worn paths that make a scene feel inhabited.
- `references/philosophy.md` — why we author in context, and why "lived-in" beats "correctly placed."
- `references/threejs-conventions.md` — Three.js geometry and material reference
- `scripts/authoring/schema.md` — geometry packet JSON schema
- `references/worked_examples/full_loop_example.md` — full worked trace with authored packets
- `references/checklists.md` — broader verification passes

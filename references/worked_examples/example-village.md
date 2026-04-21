# End-to-End Example: Village Street

This walkthrough shows the complete v4 pipeline — narrative decomposition through to validated Three.js output — for a simple village street scene.

## N1. One-sentence scene

> "A quiet village street with small houses on each side of a road, a tree, and a few people walking around."

Log to napkin:
```bash
python scripts/design_napkin.py init "Village Street v1"
python scripts/design_napkin.py note gestalt "Quiet village street, houses flanking road, people scattered"
```

## N2. Decompose to needs

```
NEEDS:
1. ground — flat plane. Done.
2. road — keepout zone down center. Done.
3. house — ONE template, repeat in rows. Randomize color.
4. person — ONE template, scatter. Not on road, not on houses.
5. tree — ONE template, place 1-2.

Count: 5 needs, 3 templates. Under budget.
```

## N3. Minimum viable primitives

Load default templates:
```bash
python scripts/template_library.py defaults library.json
python scripts/template_library.py list library.json
```

Output:
```
Templates (4):
  house_simple    footprint: 3×3  bbox: 3×4.75×3  parts: 4  mats: roof, wood_dark, brick, glass
  person_simple   footprint: 1×1  bbox: 1×1.8×1   parts: 3  mats: cloth, cloth_dark, skin
  tree_simple     footprint: 3×3  bbox: 3×4.5×3   parts: 2  mats: wood, leaf
  well_simple     footprint: 2×2  bbox: 2×1.7×2   parts: 4  mats: wood, stone
```

Check roof profile matches intent:
```bash
python scripts/braille_view.py shape triangle-tall
```
```
  triangle-tall:
    ⠀⠀⠊⠀⠀
    ⠀⠀⣿⠀⠀
    ⠀⠠⣿⠄⠀
    ⣀⣿⣿⣿⣀
```
That reads as a peaked roof. Good enough.

**Template budget: 3 templates, ~130 bytes total definition.**

## N4. Place with rules

```bash
# Init scene grid: 30 wide × 20 deep × 10 tall
python scripts/spatial_validate.py init 30 20 10 scene.json

# Define road as keepout zone (center strip)
python scripts/spatial_validate.py zone scene.json road 13 0 17 20

# Place houses from template library — left side
python scripts/template_library.py instantiate library.json scene.json house_simple 7 0 3  --name house_L1 --color "#b85533"
python scripts/template_library.py instantiate library.json scene.json house_simple 7 0 7  --name house_L2 --color "#c46838"
python scripts/template_library.py instantiate library.json scene.json house_simple 7 0 11 --name house_L3 --color "#a84828"
python scripts/template_library.py instantiate library.json scene.json house_simple 8 0 15 --name house_L4 --color "#d4885a"

# Place houses — right side
python scripts/template_library.py instantiate library.json scene.json house_simple 22 0 3  --name house_R1 --color "#987050"
python scripts/template_library.py instantiate library.json scene.json house_simple 23 0 7  --name house_R2 --color "#bb6644"
python scripts/template_library.py instantiate library.json scene.json house_simple 22 0 11 --name house_R3 --color "#b85533"
python scripts/template_library.py instantiate library.json scene.json house_simple 23 0 15 --name house_R4 --color "#c46838"

# Scatter people (not on road, not on houses — validated at placement)
python scripts/template_library.py instantiate library.json scene.json person_simple 4 0 5   --name person_01
python scripts/template_library.py instantiate library.json scene.json person_simple 11 0 9  --name person_02
python scripts/template_library.py instantiate library.json scene.json person_simple 19 0 4  --name person_03
python scripts/template_library.py instantiate library.json scene.json person_simple 25 0 12 --name person_04

# Place tree
python scripts/template_library.py instantiate library.json scene.json tree_simple 3 0 14 --name tree_01
```

## N5. Validate and verify

```bash
# Full scene validation
python scripts/spatial_validate.py check scene.json
```
```
  ✓ All checks passed
```

```bash
# Top-down view
python scripts/spatial_validate.py view scene.json
```
```
  TOP VIEW  30×20  zoom=1.0x
  ┌───────────────┐
 0│··HHH·░░··HHH··│
 1│·PHHH·░░··HHH··│
 2│··HHH·░░··HHH··│
 3│···H··░░·P·····│
 4│·PPP··░░·PPP···│
 5│··HHH·░░··HHH··│
 6│TTT···░░·······│
 7│TTT·H·░░··HHH··│
 8│TTT···░░·······│
 9│······░░·······│
  └───────────────┘
```

Houses (H) in rows on each side, road (░) down the center, people (P) on walkable tiles, tree (T) on the left. Reads as a village street.

```bash
# Braille front elevation for profile check
python scripts/braille_view.py front scene_layout.json --zoom 1
```

**→ PAUSE.** "Does this read as a quiet village street? Any template need more detail?"

## Generate Three.js

```bash
python scripts/template_library.py generate library.json scene.json --out village_code.js
```

Produces builder functions for each template and a placement function. Paste into scaffold:

```bash
python scripts/scaffold.py --title "Village Street" --camera-y 12 --camera-z 25 --out village.html
```

Insert the generated code into the scaffold's `buildModel` section.

## Data budget

| Component | Size | Tokens (~) |
|-----------|------|-----------|
| Template library (3 used) | ~130 bytes | ~35 |
| Scene file (13 objects + 1 zone) | ~1800 bytes | ~450 |
| Verification views (3 braille) | ~60 tokens | 60 |
| **Total scene in LLM context** | | **~545 tokens** |

For comparison, a raw coordinate-by-coordinate scene description would be ~3500+ tokens. The template + placement table approach compresses the scene **~85%** while remaining fully machine-readable and human-auditable.

## What this demonstrates

1. **Narrative → needs → templates → placement → verify → code** in a straight line
2. **Templates defined once**, instantiated 13 times — 90% less data than per-object definitions
3. **Road keepout zone** prevents placement errors (tested: person on road is rejected)
4. **Constraint validation** catches overlap, bounds, support, zone violations at placement time
5. **Braille/ASCII views** verify layout for ~60 tokens instead of ~450
6. **Three.js code generation** from templates + placements — no hand-written geometry
7. **The entire village fits in ~545 tokens of context** — less than this paragraph

The model never computed a coordinate. It described a scene, chose templates, declared placements, and let tools handle validation and code generation. That's the v4 thesis: compress the spatial problem until it's a language problem.

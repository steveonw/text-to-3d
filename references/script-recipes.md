# Script Recipes

Use these helpers to reduce repeatable modeling errors. Prefer them over hand-written coordinate math or broad rewrites when the request is narrow and reviewable.

## design_napkin.py — always-on working memory

The LLM's napkin. Read at the start of every turn, update after every change. Not a diary — a napkin.

```bash
# Start a new project
python scripts/design_napkin.py init "Western Saloon v1"

# Record current state
python scripts/design_napkin.py note gestalt "Warm crowded saloon, bar on left, fireplace as anchor"
python scripts/design_napkin.py note anchors "bar=left wall, fireplace=back center"
python scripts/design_napkin.py set tableE.z -3.0

# Candidate edits and reasons
python scripts/design_napkin.py candidate "Move two tables right to rebalance room"
python scripts/design_napkin.py because tableE "Clear piano clearance zone"

# Quick status (read this at start of every turn)
python scripts/design_napkin.py status

# Show full state or specific section
python scripts/design_napkin.py show
python scripts/design_napkin.py show current
```

Use the napkin for current scene state (positions, anchors, candidates). Use `worklog.py` for formal milestones, human feedback, and root cause analysis.

## layout_compare.py — spatial balance and comparison

Summarize grouped placements to spot dead zones, crowding, and balance drift. Compare before/after layouts.

```bash
# Summarize all tables in a layout
python scripts/layout_compare.py summary layout.json --group table

# Compare before and after a move
python scripts/layout_compare.py compare before.json after.json --group table
```

Layout JSON format:
```json
{
    "room": {"width": 14, "depth": 10},
    "items": [
        {"name": "tableA", "x": -2.5, "z": -1.5, "w": 1.2, "d": 1.2, "group": "table"},
        {"name": "tableB", "x": 1.0, "z": 1.5, "w": 1.2, "d": 1.2, "group": "table"}
    ],
    "zones": [
        {"name": "piano_keepout", "xmin": 3.0, "xmax": 5.5, "zmin": 3.0, "zmax": 5.0}
    ]
}
```

Output includes: item count, centroid, left/right and front/back balance, quadrant distribution, average nearest-neighbor distance, closest pair, and keepout zone collisions. Compare mode shows centroid drift and which items moved.

Use for: "is the room left-heavy?", "did that table move make things worse?", "anything in the piano zone?"

## geo.py — placements

```bash
# Rectangular grid (centered by default)
python scripts/geo.py grid --nx 5 --nz 3 --sx 2.5 --sz 3.0

# Circular ring of 16 columns, radius 8m
python scripts/geo.py ring --n 16 --r 8.0

# Half-ring (180° arc) of 6 buttresses
python scripts/geo.py ring --n 6 --r 10.0 --start 0 --end 180

# Half-ring with endpoint included (7 points spanning 0–180°)
python scripts/geo.py ring --n 6 --r 10.0 --start 0 --end 180 --include-end

# Mirror points across the X axis
python scripts/geo.py mirror --points "1,0,2 3,1,4" --axis x
```

## geo.py — profiles (dict format, default)

```bash
# Dome profile as {r, y} dicts for custom logic
python scripts/geo.py dome --r 5.0 --n 16

# Squashed dome (flatter)
python scripts/geo.py dome --r 5.0 --n 16 --squash 0.6

# Tapered column with concave curve
python scripts/geo.py taper --r-bottom 2.0 --r-top 0.8 --h 8.0 --curve 0.7 --n 16

# Semicircular arch
python scripts/geo.py arc --r 3.0 --angle 180 --n 24

# Ogee molding profile
python scripts/geo.py ogee --w 1.2 --h 0.4 --n 16

# Custom lathe profile from point pairs
python scripts/geo.py lathe --points "0,0 1,0 1.2,1 0.8,3 0,3.5"
```

## geo.py — profiles (flat format for LatheGeometry / ExtrudeGeometry)

Add `--format flat` to any profile command to get `[[x, y], ...]` arrays
that paste directly into Three.js Vector2 constructors:

```bash
# Dome as flat array
python scripts/geo.py dome --r 5.0 --n 16 --format flat

# Taper as flat array
python scripts/geo.py taper --r-bottom 2.0 --r-top 0.5 --h 6.0 --n 12 --format flat

# Ogee as flat array
python scripts/geo.py ogee --w 1.0 --h 0.3 --n 16 --format flat
```

Usage in Three.js (with modern importmap scaffold):
```javascript
// Paste the flat output into your code:
const profilePts = [ [5.0, 0.0], [4.83, 1.04], ... , [0.0, 5.0] ];
const points = profilePts.map(([x, y]) => new THREE.Vector2(x, y));
const geometry = new THREE.LatheGeometry(points, 32);
```

## geo.py — validation

```bash
# Catch negative dimensions, zero sizes, unit mixing
python scripts/geo.py validate --json params.json
```

## test_geo.py — regression tests

Run after any changes to geo.py to catch regressions:

```bash
python scripts/test_geo.py
```

Expected output: 18 tests, all passing. If any fail, fix geo.py before using it for coordinate math.

## scaffold.py

Generate a self-contained Three.js HTML scaffold with modern importmap and real OrbitControls:

```bash
# Basic scaffold to stdout
python scripts/scaffold.py

# Write to file with custom title
python scripts/scaffold.py --title "Clock Tower" --out model.html

# Custom camera position
python scripts/scaffold.py --title "Monument" --camera-y 15 --camera-z 30 --out model.html

# No grid or axes (cleaner presentation)
python scripts/scaffold.py --title "Final Render" --no-grid --no-axes --out model.html

# Custom background color
python scripts/scaffold.py --bg "#0a0a0f" --out model.html
```

The output uses Three.js r170 via ES module importmap. Still a single HTML file, no build step, but you get real OrbitControls with touch support, keyboard pan, and proper damping.

## visualize.py — 2D layout plots (optional, requires matplotlib)

Generate PNG plots to visually verify layouts before writing Three.js code. Most useful when the LLM can view the resulting image.

```bash
# Top-down floor plan from structured params
python scripts/visualize.py plan layout.json --out layout.png

# Plot geo.py placement output (where things land)
python scripts/visualize.py placements placements.json --out grid.png

# Simple bounding box proportion check
python scripts/visualize.py boxes boxes.json --out boxes.png

# Front elevation — verify vertical stacking
python scripts/visualize.py elevation stack.json --out front_elevation.png

# Side elevation
python scripts/visualize.py elevation stack.json --view side --out side_elevation.png
```

Layout JSON format:
```json
{
    "unit": "m",
    "room": {"width": 14, "depth": 10},
    "parts": [
        {"name": "bar", "x": -5.5, "z": 0, "w": 2, "d": 8, "tier": "hero"},
        {"name": "table1", "x": 2, "z": 2, "w": 1.2, "d": 1.2, "tier": "mid"},
        {"name": "fireplace", "x": 0, "z": 4.5, "w": 3, "d": 0.6, "tier": "hero"}
    ]
}
```

Elevation JSON format (y is CENTER position, h is full height):
```json
[
  {"name": "base", "x": 0, "z": 0, "y": 1.0, "w": 14, "d": 10, "h": 2.0},
  {"name": "walls", "x": 0, "z": 0, "y": 4.5, "w": 12, "d": 8, "h": 5.0},
  {"name": "dome", "x": 0, "z": 0, "y": 10.5, "w": 7, "d": 7, "h": 3.0}
]
```

Floor plans are color-coded by detail tier (hero=blue, mid=green, far=gray). Elevations show Y-center and bottom-to-top range for each part, with a ground line at y=0. Any visible gap between stacked parts = stacking error.

Use floor plans after Stage 4 to verify layout. Use elevations after Stage 7 to verify stacking math and again in Stage 10a for post-code verification.

If matplotlib is not installed, the script exits with a message. The skill works without it — ASCII + walkthrough + cross-check table covers the same ground, just less precisely.

## worklog.py — persistent scratchpad

The LLM's notebook. Write things down during the project, read them back when context gets long.

```bash
# Start a new project log
python scripts/worklog.py init "Lighthouse v1.0"

# Log stage completions
python scripts/worklog.py add S1 "Classic lighthouse, ~20m tall, 3 main parts"
python scripts/worklog.py add S4 "Cross-check table passed, all ranges consistent"

# Log human decisions (do this immediately after every human response)
python scripts/worklog.py add HUMAN "User wants pointed dome, not rounded"
python scripts/worklog.py add DECIDED "Base diameter 6m — confirmed by user"
python scripts/worklog.py add UNCERTAIN "Railing height — using 1.1m placeholder"

# Log things to fix later
python scripts/worklog.py add TODO "Fix window spacing on north face"

# Read the full log (do this at the start of long conversations)
python scripts/worklog.py read

# Read just human feedback or TODOs
python scripts/worklog.py read HUMAN
python scripts/worklog.py read TODO

# Quick summary: what's decided, what's uncertain, what's outstanding
python scripts/worklog.py status
```

Use the worklog for any project that spans more than 5–6 exchanges. Write early, write often, read back before every pause point.

## parameter_table_generator.py

Generate a clean markdown parameter table from JSON.

Example JSON:
```json
{
  "unit": "m",
  "parameters": {
    "baseWidth": {"value": 12, "status": "confirmed", "notes": "front facade"},
    "domeRadius": {"value": 3.2, "status": "inferred", "depends_on": ["baseWidth"]}
  }
}
```

Command:
```bash
python scripts/parameter_table_generator.py params.json --out params.md
```

## scene_inventory.py

Inspect an existing Three.js file before refinement.

```bash
# Markdown summary (default)
python scripts/scene_inventory.py model.html

# JSON for programmatic use
python scripts/scene_inventory.py model.html --format json --out inventory.json
```

Use the inventory to identify:
- existing geometry types and counts
- whether InstancedMesh is already used
- what helper functions and PARAMS keys exist
- whether controls/helpers are present and should be preserved

## threejs_patch_diff.py

### Two-file comparison (includes function-body unified diffs)
```bash
python scripts/threejs_patch_diff.py v1.html v2.html
python scripts/threejs_patch_diff.py v1.html v2.html --note "dome was raised in v2"
python scripts/threejs_patch_diff.py v1.html v2.html --format json
```

### Single-file + change note (scoped edit plan)
```bash
python scripts/threejs_patch_diff.py model.html --note "raise dome and reduce drum height"
```

The two-file mode outputs actual unified diffs for each function that changed,
plus symbol-level additions/removals and risk assessment. Use it to review
what a pass actually touched before committing.

## braille_view.py — braille verification views and shape vocabulary (v4 NEW)

Renders spatial layouts as braille text for cheap inline verification. Also provides a shape vocabulary for A/B profile comparison and piecewise curve-to-coordinate conversion.

```bash
# Orthographic braille views (costs ~20 tokens each vs ~150 for ASCII)
python scripts/braille_view.py top layout.json --zoom 1
python scripts/braille_view.py front layout.json --zoom 1
python scripts/braille_view.py side layout.json --zoom 1

# Zoom levels: 0.5 (close/detail), 1 (normal), 2 (far/overview), 4 (city-scale)
python scripts/braille_view.py front layout.json --zoom 2

# Show all reference shapes in the vocabulary
python scripts/braille_view.py shapes

# Show a single shape for comparison
python scripts/braille_view.py shape arch-pointed
python scripts/braille_view.py shape dome-onion
python scripts/braille_view.py shape triangle-tall

# Convert piecewise curve description to coordinate array
python scripts/braille_view.py curve "FLAT(3) GENTLE-ARC(5) STEEP-ARC(3) POINTED(1) mirror"
```

Layout JSON format is the same as `visualize.py`:
```json
{
    "unit": "m",
    "room": {"width": 14, "depth": 10, "height": 8},
    "parts": [
        {"name": "base", "x": 0, "z": 0, "y": 1.0, "w": 14, "d": 10, "h": 2.0}
    ]
}
```

Available curve segments (heading-based turtle model, all connect with continuous heading):
- **Upward:** `FLAT` (0°), `GENTLE-ARC` (15°), `MEDIUM-ARC` (30°), `STEEP-ARC` (60°), `SHARP-ARC` (80°)
- **Vertical:** `POINTED` (forces 90°), `STRAIGHT` (alias for FLAT)
- **Downward:** `DOWN-GENTLE` (-15°), `DOWN-MEDIUM` (-30°), `DOWN-STEEP` (-60°)
- Append `mirror` to auto-mirror the profile around its rightmost X coordinate.

### Verification with scoring and diff planes (v4.0.1)

Compare a generated shape against a target/template. Produces aligned diff planes, score vector, dominant failures, and patch recommendations.

```bash
# Verify a shape against its target template
python scripts/braille_view.py verify shape.json --target target.json --view front --zoom 1 \
    --name cottage_01 --template house_gable_small

# Output includes:
#   status: pass / needs_patch / needs_rebuild
#   scores: profile_alignment, support_integrity, symmetry_deviation, etc.
#   dominant_failures: ranked list of physical issues
#   shape_front / target_front / missing_front / extra_front: aligned diff planes
#   recommended_patches: minimal repair actions
```

Views: `--view top`, `--view front`, `--view side`. Run all three for full inspection.

Use braille views for quick iteration checks. Use ASCII/PNG for formal planning where labels are needed.

## spatial_validate.py — draw-and-validate constraint checker (v4 NEW)

Placement IS measurement. Every object placed is immediately validated against constraints. Errors are caught at drop time.

```bash
# Initialize a scene grid (width × depth × height)
python scripts/spatial_validate.py init 30 20 10

# Define keepout zones (roads, pathways, clearance areas)
python scripts/spatial_validate.py zone scene.json road 13 0 17 20
python scripts/spatial_validate.py zone scene.json piano_keepout 3 8 6 12

# Place an object — validation runs automatically (checks bounds, overlap, support, zones)
# Args: scene.json name x y z w h d
python scripts/spatial_validate.py place scene.json house_01 8 0 3 3 4.75 3 --char H
python scripts/spatial_validate.py place scene.json table_01 5 0 8 1.2 0.75 1.2 --char T

# If placement is rejected, you get:
#   ✗ house_02 overlaps with house_01
#     Overlap: 1.5u on X, 2.0u on Z
#     → Shift house_02 by 1.5u on X or 2.0u on Z

# Validate entire scene (all six named errors)
python scripts/spatial_validate.py check scene.json

# Spatial queries
python scripts/spatial_validate.py query scene.json distance table_01 bar_01
python scripts/spatial_validate.py query scene.json overlap house_01 house_02
python scripts/spatial_validate.py query scene.json fits 3 2.5 3 --at 10 0 5

# Quick top-down text view
python scripts/spatial_validate.py view scene.json --zoom 1
```

Checks performed on every placement:
- **Bounds:** Object within grid?
- **Overlap:** Collides with existing objects?
- **Support:** Floating in air? (objects with y > 0 need something beneath)
- **Zones:** Inside a keepout zone? (roads, pathways, clearance areas)
- **Scale:** Extreme size ratio between objects?

Use `check` for full scene validation including quadrant balance, scale uniformity, and zone violations. Zones appear as `░` in the view.

## template_library.py — template store and instantiation (v4 NEW)

Define reusable object templates with footprint, bounding box, and parts. Instantiate them into scenes. Generate Three.js code from templates + placement table.

```bash
# Initialize empty library
python scripts/template_library.py init library.json

# Load 4 default templates (house, person, tree, well)
python scripts/template_library.py defaults library.json

# List all templates with dimensions and materials
python scripts/template_library.py list library.json

# Show detailed template info
python scripts/template_library.py show library.json house_simple

# Add a custom template from a JSON file
python scripts/template_library.py add library.json tower_v1 --from-file tower.json

# Add a template inline
python scripts/template_library.py add library.json crate_v1 \
    --parts '[{"shape":"box","w":1,"h":1,"d":1,"material":"wood"}]' \
    --footprint 1 1 --bbox 1 1 1 --name "Wooden Crate"

# Instantiate a template into a scene (uses bbox from template)
python scripts/template_library.py instantiate library.json scene.json house_simple 8 0 3 \
    --name house_L1 --color "#b85533"

# Instantiate with rotation (e.g., fence running along Z instead of X)
python scripts/template_library.py instantiate library.json scene.json fence_section 9 0 19 \
    --name fence_W1 --rotation-y 90

# Generate Three.js builder functions + placement code from scene
python scripts/template_library.py generate library.json scene.json --out scene_code.js

# Generate centered (subtract offset from all positions — use for final output)
python scripts/template_library.py generate library.json scene.json --center 15,15 --out scene_code.js
```

Template JSON format:
```json
{
    "name": "Simple House",
    "parts": [
        {"shape": "box", "w": 3, "h": 2.5, "d": 3, "material": "brick", "y_offset": 1.25},
        {"shape": "cone", "r": 2.5, "h": 1.5, "sides": 4, "material": "roof", "y_offset": 3.25}
    ],
    "footprint": [3, 3],
    "bounding_box": [3, 4.75, 3],
    "attachments": {
        "surface_top": {"y": 2.5, "area": [3, 3]},
        "door": {"face": "south", "y": 0, "w": 0.6, "h": 1.2}
    },
    "randomize": {
        "parts.0.color": ["#b85533", "#c46838", "#a84828"]
    }
}
```

Supported shapes: `box`, `sphere`, `cylinder`, `cone`. Each part has position offsets (`x_offset`, `y_offset`, `z_offset`) and optional rotation (`rotation_x`, `rotation_y`, `rotation_z` in degrees) relative to the template origin.

**Instance rotation:** `--rotation-y 90` rotates the whole template group. The bounding box w↔d is automatically swapped so spatial_validate checks the rotated footprint. Use for fences, walls, benches, or any template that needs to face a different direction.

**Centering:** `--center cx,cz` subtracts the offset from all positions in the generated code. Edit scenes in positive grid coords (easier to reason about), center as the last step before output. If you need to edit again, scene.json still has the original coords.

The `generate` command produces Three.js code with one builder function per template and a `buildModel` function that instantiates all objects from the scene file. Paste into the scaffold or use as a module. The scaffold's `matByName()` palette must be available.


## path_walk.py — Narrated spatial walk

Walk a line through the scene and report what's nearby at each step. Catches path discontinuities, dead gaps, chokepoints, and zone transitions.

```bash
# Walk the central axis
python scripts/path_walk.py scene.json --axis-x 18 --from-z 0 --to-z 40

# Custom step size and scan radius
python scripts/path_walk.py scene.json --axis-x 18 --from-z 0 --to-z 40 --step 1 --radius 4

# Walk a custom path (waypoints)
python scripts/path_walk.py scene.json --waypoints "18,0 18,9 20,15 18,20"

# Auto-detect: walks center of grid
python scripts/path_walk.py scene.json

# JSON output for machine consumption
python scripts/path_walk.py scene.json --axis-x 18 --from-z 0 --to-z 40 --json
```

**Output includes:**
- Per-step report: nearest objects with direction, distance, height
- Dead gaps: stretches where nothing is ahead within range
- Chokepoints: narrow passages between objects on both sides
- Zone transitions: when the dominant ahead-object changes

**When to use:** After placement passes validation. Before generating code. The path walk catches "this feels wrong" issues that braille and validation can't: disconnected stairs, awkward entrances, props intruding into movement lanes, empty dead zones.

**Verification stack:**
1. `spatial_validate.py check` — exact spatial (overlaps, bounds, support)
2. `braille_view.py` — silhouette sanity (gross shape, nothing floating)
3. `path_walk.py` — experiential sanity (approach logic, gaps, pacing)
4. Walk mode (scaffold) — visual sanity (human eyes, composition, feel)

## scaffold.py — Walk mode

Every scaffold now includes a built-in walk mode:
- **F key** or button → toggle walk/orbit
- **WASD / Arrows** → move
- **Mouse** → look (pointer lock)
- **Q / E** → rotate left/right (keyboard look, no mouse needed)
- **R / T** → pitch up/down
- **Esc** → return to orbit mode
- HUD shows position coordinates and compass direction

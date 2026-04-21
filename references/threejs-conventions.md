# Three.js output conventions

Read this before writing any Three.js model code.

## Default output target

Self-contained single HTML file. All JS inline. No build step.

Use ES module importmap for modern Three.js with real OrbitControls:
```html
<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.170/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.170/examples/jsm/"
  }
}
</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
// ... rest of scene
</script>
```

Use `scripts/scaffold.py` to generate the boilerplate instead of writing it by hand. Then replace the PARAMS and buildModel sections.

## Code structure rules

1. **One PARAMS object at the top.** Every dimension, offset, radius, and count lives here. No magic numbers in geometry code.
2. **One `buildModel(scene)` function.** Returns the root group. Build sub-functions for each major part.
3. **Name your groups and meshes.** `group.name = 'tower_main'` — makes debugging in the browser console possible.
4. **Y is up.** Origin at ground center unless the user specifies otherwise.
5. **Consistent units.** State the unit in PARAMS. Default to meters for architecture, centimeters for small props.

## Stacking rule (critical — prevents the most common bug)

Three.js BoxGeometry and CylinderGeometry are centered at their origin. When stacking parts vertically:

```
part.position.y = sum_of_heights_below + own_height / 2
```

Expressed as PARAMS:
```javascript
// CORRECT: center of tower is half its height above the base top
tower.position.y = PARAMS.baseHeight + PARAMS.towerHeight / 2;

// WRONG: bottom half of tower clips into base
tower.position.y = PARAMS.baseHeight;
```

Show the stacking math explicitly in Stage 7 (coordinate map). Verify in Stage 10a (ASCII verification) that the Y-center of each part in code matches the Y-center visible in the front elevation diagram.

## Complexity budget

| Object class       | Target mesh count | Max code lines |
|--------------------|-------------------|----------------|
| Simple prop        | < 25              | < 375          |
| Medium (vehicle)   | 25–75             | 375–750        |
| Complex (building) | 50–150            | 625–1250       |
| Monument / scene   | 75–250            | 1000–1875      |

If the mesh count exceeds 200, suggest splitting into separate files or using instanced meshes.

## Geometry patterns

### Prefer
- `BoxGeometry`, `CylinderGeometry`, `SphereGeometry` for blockout
- `LatheGeometry` for rotationally symmetric profiles (domes, columns, moldings)
- `ExtrudeGeometry` with `THREE.Shape` for cross-section sweeps
- `InstancedMesh` for repeated elements (windows, columns, bricks) — use when count > 8

### Avoid
- Manual vertex manipulation unless strictly necessary
- BufferGeometry built from raw arrays for simple shapes
- More than 3 nesting levels of groups

## Material defaults

Use MeshStandardMaterial for everything unless there's a specific reason not to.

### Standard palette

| Intent           | Color        | roughness | metalness | Notes                          |
|------------------|-------------|-----------|-----------|--------------------------------|
| Stone/concrete   | `0xc4b8a8`  | 0.85      | 0.0       | Warm gray                      |
| Brick/sandstone  | `0xa0522d`  | 0.75      | 0.0       | Muted red-brown                |
| Metal (aged)     | `0x555555`  | 0.45      | 0.8       | Dark steel                     |
| Metal (polished) | `0xcccccc`  | 0.15      | 0.95      | Silver/chrome                  |
| Wood (structural)| `0x5c3a1e`  | 0.80      | 0.0       | Dark — beams, posts            |
| Wood (furniture) | `0x8b6914`  | 0.70      | 0.0       | Medium — tables, chairs        |
| Plaster/wall     | `0xd4c5a9`  | 0.90      | 0.0       | Light — contrast with wood     |
| Floor (dark)     | `0x6b4423`  | 0.85      | 0.0       | Ground the scene               |
| Glass            | `0x88bbdd`  | 0.05      | 0.0       | Use MeshPhysicalMaterial, transmission: 0.9 |
| Ground/grass     | `0x556b2f`  | 0.90      | 0.0       | Muted green                    |
| Marble (white)   | `0xf0ece0`  | 0.40      | 0.0       | Warm white, not pure white     |
| Accent           | `0xcc4444`  | 0.50      | 0.0       | Highlight/feature              |
| Blockout/WIP     | `0xcccccc`  | 0.80      | 0.1       | Neutral placeholder            |

### Material rules
- Assign materials to named variables: `const matStone = new THREE.MeshStandardMaterial({...});`
- Reuse the same material variable for same-material parts (performance + consistency).
- **No two adjacent major surfaces should share the same material.** The eye needs contrast to read depth and separate overlapping forms.
- Don't use MeshBasicMaterial for anything that should receive light.
- Enable shadows on key meshes: `mesh.castShadow = true; mesh.receiveShadow = true;`

### Interior scenes — minimum 5 material zones

| Zone        | Example                           | Why distinct                    |
|-------------|-----------------------------------|---------------------------------|
| Structural  | Dark wood (beams, posts)          | Heavier visual read             |
| Furniture   | Medium wood (tables, chairs)      | Lighter than structure          |
| Walls       | Plaster/paint                     | Contrast with wood              |
| Floor       | Dark planks                       | Ground the scene                |
| Accent      | Metal/glass/stone                 | Bar fixtures, fireplace, mugs   |

## Detail tier budget

Not every part deserves the same geometry investment. Assign tiers in Stage 9:

| Tier | Rule                              | Geo budget    | Example             |
|------|-----------------------------------|---------------|---------------------|
| Hero | Camera will be close, tells story | 6–12 meshes   | Bar counter, fireplace |
| Mid  | Visible but not focal             | 3–5 meshes    | Table + chairs set  |
| Far  | Background fill                   | 1–2 meshes    | Wall shelf, barrel  |

Build hero props first. Fill mid-tier with repeated modular pieces. Far-tier props can be single primitives with material contrast.

## Placement helpers

Use `scripts/geo.py` to pre-compute arrays before coding:

```bash
# Columns around a rotunda
python scripts/geo.py ring --n 16 --r 8.0

# Window grid on a facade
python scripts/geo.py grid --nx 5 --nz 3 --sx 2.5 --sz 3.0

# Tapered minaret profile for LatheGeometry
python scripts/geo.py taper --r-bottom 1.5 --r-top 0.4 --h 12 --n 20 --curve 0.7
```

Paste the JSON output into the PARAMS section or use it to inform the buildModel function.

## Common antipatterns

| Problem | Fix |
|---------|-----|
| Hardcoded position `mesh.position.set(3.7, 2.1, 0)` | Derive from PARAMS: `PARAMS.baseHeight + PARAMS.wallHeight / 2` |
| Duplicate geometry for symmetric parts | Use `mirror` or `clone()` + `scale.x = -1` |
| Flat shading on curved surfaces | Increase segment count or use `computeVertexNormals()` |
| No shadows | Set `mesh.castShadow = true; mesh.receiveShadow = true;` on key meshes |
| Giant single function | Break into `buildBase()`, `buildTower()`, `buildRoof()`, etc. |
| Camera too close or too far | Set camera distance to ~2–3x the object's bounding radius |
| Everything same material | Assign at least 3–5 distinct materials by role |
| `position.y = PARAMS.baseHeight` | Wrong — use `PARAMS.baseHeight + ownHeight / 2` (stacking rule) |

## The five common spatial errors

LLMs make these errors reliably and repeatedly. Name them so they're checkable. Check for all five after every code pass.

### Error 1: The Y/Z swap
Three.js Y is up. Human language is ambiguous — "depth" sometimes means Y, sometimes Z. "The shelf is 2m deep" — deep into the wall (Z) or tall (Y)?

**Rule:** In this project, "height" ALWAYS means Y. "Depth" ALWAYS means Z. "Width" ALWAYS means X. State this in PARAMS comments.

### Error 2: The half-height clip
BoxGeometry and CylinderGeometry are centered at their origin. A box at `position.y = 0` extends below the floor.

**Rule:** `position.y = sum_of_heights_below + ownHeight / 2` (see stacking rule above)

### Error 3: The invisible interior
Objects inside other objects fail to render if: the camera near plane clips them, room walls have no backface rendering, or there's no interior light source.

**Rule:** Interiors need `side: THREE.DoubleSide` on walls OR open-top rooms, at least one interior point light, and camera near < 0.1.

### Error 4: The uniform scale
Everything ends up the same size because the LLM defaulted to similar values. Mugs are 30cm tall, chairs are 50cm wide, barrels are 1m — nothing looks right because scale variation is flattened.

**Rule:** After code, list the 3 smallest and 3 largest objects with their actual rendered dimensions. Is the ratio plausible? Check against the scale anchors from Stage 2.

### Error 5: The symmetric default
LLMs prefer symmetry and centering. Real spaces are asymmetric. The bar is against one wall, not centered. Tables cluster, they don't form perfect grids.

**Rule:** In the floor plan, check that at least 2 of 4 quadrants have meaningfully different content. Intentional symmetry (like a formal facade) is fine — accidental symmetry from laziness is not.

### Error 6: The rotation axis mismatch
Three.js `rotation.y = θ` maps local +Z to world `(sin θ, 0, cos θ)`. If you compute the angle for the wrong local axis, objects rotate to face the wrong direction — and one placement may work by coincidence while others are visibly wrong.

Common trap: a bench's depth runs along local +Z, but you use `atan2(dirZ, dirX)` which aligns local +X with the wall direction. Result: bench faces along the wall instead of facing inward. One bench works by coincidence when the formula happens to produce the same angle for that specific wall orientation.

**Rule:** When rotating an object to face a direction, know which local axis is "forward" for that object:
- To align local +Z with a direction vector `(dx, dz)`: `rotation.y = atan2(dx, dz)`
- To align local +X with a direction vector `(dx, dz)`: `rotation.y = atan2(dz, dx)`

**Test:** If only some instances of a repeated rotated element look correct, you have this bug. The ones that work are coincidences where both formulas produce the same angle.

## Horizontal alignment rule (the stacking rule's sibling)

The stacking rule handles vertical placement: `position.y = sum_below + ownHeight/2`. The same principle applies horizontally when placing objects against surfaces:

```
position along surface normal = surface_line - gap - objectDepth/2
```

When placing an object "against" a wall or surface:
- Identify which surface of the object faces the wall (e.g., "back face")
- Offset by half the object's dimension in that direction plus the desired gap
- **State this explicitly:** "bench back face sits 0.05m from wall line" → `push = 0.05 + depth/2`

If you just set position = wall position, the center of the object lands on the wall and half of it sticks through. This is the horizontal equivalent of the half-height clip.

## Spatial noise for props (interior scenes)

After placing furniture and props on a grid, apply small random rotations and offsets to non-structural items to shift from "CAD diagram" to "inhabited space":

```javascript
// Apply ONLY to movable props, never walls/floors/structure
// Apply AFTER the verification pass
// Use seeded random for reproducibility
function jitter(mesh, rotDeg = 5, posMet = 0.1) {
    mesh.rotation.y += (Math.random() - 0.5) * rotDeg * Math.PI / 180 * 2;
    mesh.position.x += (Math.random() - 0.5) * posMet * 2;
    mesh.position.z += (Math.random() - 0.5) * posMet * 2;
}
```

Guidelines: tables ±5° rotation and ±0.1m offset, chairs ±15° rotation (pulled out, turned slightly), props on surfaces ±0.05m offset from center.

## Version naming

Name each iteration in a comment at the top of the file:
```javascript
// Clock Tower v1.0 — blockout massing
// Clock Tower v1.1 — dome rebalance
// Clock Tower v2.0 — facade detail pass
```

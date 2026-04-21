# Braille Verification v2

Use Unicode Braille as a dense text-mode raster for grounded scene inspection. The system derives aligned top/front/side occupancy planes from real geometry, compares them against template or constraint targets, computes physical score vectors, and proposes minimal repair patches. Braille is used to compress geometry for critique, not to encode freeform meaning.

## Core rule

**Use Braille to compress geometry, not meaning.**

- Derive Braille from real scene structure
- Compare aligned spatial planes
- Compute grounded physical scores
- Patch the scene
- Re-check

Do not hash freeform natural language into Braille. Do not treat Braille as a universal semantic encoding.

## Technical foundation

### Dot position mapping

```
Braille cell layout:        Bit values:
┌───┬───┐                   ┌───┬───┐
│ 1 │ 4 │  ← row 0 (top)   │ 1 │ 8 │
│ 2 │ 5 │  ← row 1         │ 2 │16 │
│ 3 │ 6 │  ← row 2         │ 4 │32 │
│ 7 │ 8 │  ← row 3 (bot)   │64 │128│
└───┴───┘                   └───┴───┘

Unicode codepoint = 0x2800 + sum of active bit values
Full block: 255 → U+28FF = ⣿    Empty: 0 → U+2800 = ⠀
```

Each braille character encodes a 2-wide × 4-tall binary grid in a single codepoint (~1 token). This is approximately 8× denser than equivalent ASCII.

### 3D encoding convention

- **X-axis:** characters left to right. Each char = 2 units wide.
- **Y-axis:** dot rows within character. Bottom = row 3 (dots 7,8), top = row 0 (dots 1,4).
- **Z-axis:** separate layer markers `─Z0─` `─Z1─` or separate lines per Z-slice.

### Zoom levels

| Zoom | 1 braille char covers | Use for |
|------|----------------------|---------|
| Far (×4) | 8w × 16h units | Whole-scene layout |
| Normal (×1) | 2w × 4h units | Single building, room |
| Close (×0.5) | 1w × 2h units | Detail, profiles |

## Inspection bundle

For every object, template instance, or scene chunk under review, generate aligned verification planes.

### Required planes

| Plane | Purpose |
|-------|---------|
| `shape_top` | Top-down occupancy footprint |
| `shape_front` | Front elevation silhouette |
| `shape_side` | Side elevation profile |
| `target_top/front/side` | Expected shape from template or constraint |
| `missing_top/front/side` | Cells in target but not in shape (underbuilt) |
| `extra_top/front/side` | Cells in shape but not in target (overbuilt) |
| `unsupported_mask` | Occupied cells with nothing below them |
| `collision_mask` | Cells where two objects overlap |

### Optional planes

| Plane | Purpose |
|-------|---------|
| `type_top/front/side` | Semantic overlay (see Semantic planes below) |
| `symmetry_mask` | Asymmetric cells where symmetry expected |
| `section_x/y/z` | Cross-section at specific coordinate |
| Local high-res patch | Zoomed view of failure region |

### Alignment contract

All planes for a given inspection must share:
- Same bounds for the same view direction
- Same raster resolution
- Explicit axis labels
- Explicit scale

## Scoring

Do not use one vague aggregate score. Use a grounded score vector tied to geometry and constraints.

### Required metrics

| Metric | What it measures |
|--------|-----------------|
| `footprint_alignment` | Top-view overlap between shape and target (0–1) |
| `front_profile_alignment` | Front elevation match (0–1) |
| `side_profile_alignment` | Side elevation match (0–1) |
| `support_integrity` | Fraction of occupied cells that have support below (0–1) |
| `collision_penalty` | Number of cells where objects overlap (0 = clean) |
| `estimated_patch_cost` | Number of discrete repair operations needed |

### Recommended additional metrics

| Metric | What it measures |
|--------|-----------------|
| `symmetry_deviation` | Asymmetry where symmetry is expected (0 = symmetric) |
| `template_fit_score` | Overall match to declared template intent (0–1) |
| `clearance_violation_penalty` | Cells violating keepout zones |
| `curve_smoothness_penalty` | Step artifacts in expected-smooth profiles |

Scoring must be tied to geometry and constraints, not string similarity or hash distance.

### Honest limits of braille for model reasoning

**Scores are the primary machine-facing output. Diff planes are supplementary.**

The score vector (alignment, support, collision, patch cost) is computed by Python — these are reliable numbers the model can act on directly. The braille diff planes (shape, target, missing, extra) are visual aids.

What the model can do with braille planes:
- Detect gross shape differences ("this has dots, that is mostly empty")
- Compare overall silhouettes ("roughly triangular vs roughly rectangular")
- Confirm symmetry or asymmetry at block level

What the model cannot reliably do:
- Identify which specific dot in which braille character is wrong
- Perform cell-level spatial reasoning within braille patterns
- Reconstruct precise geometry from braille alone

**Decision rule:** Use scores for deciding what to fix. Use diff planes for confirming the scores make sense. Use ASCII or PNG views when cell-level precision matters.

## Output contract

Each verification block should include:

```
inspect: cottage_01
template: house_gable_small
status: needs_patch

view: front
bounds: x=[0,32], z=[0,20]
scale: 1 cell = 0.25m
axes: horizontal=x, vertical=z

scores:
  footprint_alignment: 0.94
  front_profile_alignment: 0.81
  side_profile_alignment: 0.86
  support_integrity: 0.98
  collision_penalty: 0
  symmetry_deviation: 0.11
  estimated_patch_cost: 3

dominant_failures:
  1. extra roof mass on front-right
  2. left/right asymmetry in gable width
  3. doorway opening missing in target zone

shape_front:
  ⣀⣤⣶⣿⣿⣶⣤⣀
  ...

target_front:
  ⣀⣤⣶⣿⣿⣶⣤⣀
  ...

extra_front:
  ........⣀⣀
  ...

missing_front:
  ...⣀⣀....
  ...

unsupported_mask:
  ............
  ...

collision_mask:
  ............
  ...

recommended_patches:
  1. remove volume x=22..24 z=13..15
  2. extend left roof slope by 2 cells
  3. carve doorway opening x=14..16 z=0..6
```

## Critique loop

Use this repair loop whenever verification is enabled:

1. Generate or place the scene
2. Derive aligned verification planes
3. Compute scorecard
4. Identify the largest physically meaningful failure
5. Propose the smallest valid patch set
6. Apply patch
7. Re-run verification
8. Stop when scores pass thresholds or no safe improvement remains

### Patch priority order

1. Collisions (objects overlapping)
2. Unsupported mass (floating geometry)
3. Gross silhouette mismatch (wrong shape)
4. Symmetry mismatch (where symmetry is expected)
5. Openings, details, cosmetic refinements

**Do not fix decorative issues before structural ones.**

## Patch vocabulary

Prefer minimal, explicit repair actions:

| Patch type | Description |
|-----------|-------------|
| `add_volume` | Fill cells at specified coordinates |
| `remove_volume` | Clear cells at specified coordinates |
| `shift_object` | Move object by offset |
| `resize_axis` | Scale object along one axis |
| `raise_lower` | Adjust Y position |
| `rotate_canonical` | Snap to canonical orientation |
| `swap_template` | Replace with different template |
| `carve_opening` | Cut door/window/arch from solid |
| `add_support` | Insert support element below floating mass |
| `replace_curve` | Swap curve segment with piecewise reference |
| `adjust_slope` | Modify angle of inclined surface |

Patches should reference coordinates, bounds, or template parts. Not vague descriptions.

## Template integration

Templates should expose verification targets where available:

| Target | Purpose |
|--------|---------|
| Canonical top profile | Expected footprint shape |
| Canonical front profile | Expected front silhouette |
| Canonical side profile | Expected side silhouette |
| Expected support pattern | Where the object contacts ground/surface |
| Allowed variation bounds | How much instancing can deviate |
| Symmetry expectation | Which axes should be symmetric |
| Required opening zones | Doors, windows, arches that must exist |
| Clearance constraints | Keepout zones around the object |

Verification compares generated output against declared template intent, not only against generic scene occupancy.

## Resolution strategy

Use a two-pass inspection:

### Global pass
- Lower resolution (zoom ×2 or ×4)
- Whole object or whole scene
- Catches: footprint errors, profile mismatches, placement problems, obvious collisions

### Local patch pass
- Higher resolution (zoom ×1 or ×0.5)
- Focused on failure regions identified by global pass
- Catches: support gaps, opening issues, curve problems, fit errors

Do not use maximum density everywhere by default. Spend resolution tokens where failures are.

## Semantic planes

When semantic overlays are needed, use a small aligned symbol map as a separate plane. Do not overload braille glyphs with material meaning.

```
. empty    w wall    r roof    d door    g glass
f floor    s support c chassis t tire    e error
```

Keep semantic alphabets small and stable. Prefer an extra plane over an overloaded custom glyph system.

## Curve handling

Do not trust smooth natural-language curve requests directly. Convert curves into sampled or piecewise representations first, then verify their projections.

When checking curves, prefer:
- Endpoint alignment
- Monotonicity where expected
- Roughness penalty
- Profile deviation from target

Use Braille views to validate resulting profiles, not to define curves from scratch.

### Shape vocabulary for A/B comparison

These reference shapes are for the narrative decomposition phase — choosing which profile to aim for before generating geometry.

```
triangle-equilateral    triangle-tall    triangle-wide
arch-round              arch-pointed     arch-flat
dome-round              dome-onion       buttress
box                     cylinder         cross-section-I/L
```

Use `python scripts/braille_view.py shapes` to display all references.

Describe complex curves as piecewise segments:
```
roofline: FLAT(3) → GENTLE-ARC(4) → STEEP-ARC(3) → POINTED(1) → mirror
```

Convert to coordinates with `python scripts/braille_view.py curve "..."`.

### How piecewise segments work

Segments use a heading-based turtle model. The cursor carries a position and a direction. Each segment is a circular arc that travels a given length while turning the heading by a specified number of degrees. Segments connect end-to-end with continuous heading — no sharp kinks unless explicitly intended.

Starting heading is 0° (rightward). Positive turn = counterclockwise (curves upward for profiles).

| Segment | Turn | Effect |
|---------|------|--------|
| `FLAT(L)` | 0° | Straight in current direction |
| `GENTLE-ARC(L)` | 15° | Slight upward curve |
| `MEDIUM-ARC(L)` | 30° | Moderate curve |
| `STEEP-ARC(L)` | 60° | Sharp curve |
| `SHARP-ARC(L)` | 80° | Near-right-angle |
| `POINTED(L)` | — | Forces heading to 90° (straight up) |
| `STRAIGHT(L)` | 0° | Alias for FLAT |
| `DOWN-GENTLE(L)` | -15° | Slight downward curve |
| `DOWN-MEDIUM(L)` | -30° | Moderate downward |
| `DOWN-STEEP(L)` | -60° | Sharp downward |

Append `mirror` to reflect the profile around its rightmost X coordinate. Useful for symmetric profiles (roofs, arches, domes).

**Example: pointed roof**
```
FLAT(3) GENTLE-ARC(4) STEEP-ARC(3) POINTED(1) mirror
```
This goes 3 units flat, curves up gently for 4, steepens for 3, goes 1 unit straight up to the peak, then mirrors. The result is a smooth, monotonically rising profile that peaks and descends symmetrically.

Output is a `[[x, y], ...]` array suitable for Three.js `Vector2` constructors:
```javascript
const profilePts = [...]; // from braille_view.py curve
const points = profilePts.map(([x, y]) => new THREE.Vector2(x, y));
const geometry = new THREE.LatheGeometry(points, 32);
```

## What not to do

- Do not hash freeform text into Braille for scene generation
- Do not rely on Braille as the only inspection output
- Do not overload one glyph alphabet with too many meanings
- Do not use decorative formatting (color, bold, italic) as primary machine-facing channels
- Do not optimize for clever encoding over repairability
- Do not fix cosmetic issues before structural ones
- Do not use maximum resolution everywhere

## Design principle

Braille verification should make failures easier to detect, explain, and patch.

A good verification representation is:
- **Compact** — fits in minimal context
- **Grounded** — derived from real geometry, not hashed from text
- **Aligned** — all planes share bounds and resolution
- **Comparable** — diff planes show exactly what's wrong
- **Patch-oriented** — failures map directly to repair actions
- **Scored** — numeric metrics, not vibes

If a denser encoding makes critique harder, do not use it.

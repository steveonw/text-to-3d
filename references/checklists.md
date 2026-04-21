# Checklists

## Scene type classification (decide in Stage 1)

| Aspect | Exterior object | Interior scene |
|--------|----------------|----------------|
| Primary diagram | Front + side elevation | Floor plan + wall section |
| Walkthrough | Walk around it | Walk through it |
| Camera default | Outside, orbiting | Inside, eye height (~1.6m) |
| Lighting | Sun + sky (directional) | Interior points + ambient |
| Material focus | Facade materials, weather | Surface variety, warmth |
| Stacking focus | Vertical (base→tower→dome) | Horizontal (zones, furniture) |
| Primary error | Silhouette is wrong | Layout / flow is wrong |
| Jitter applies | Rarely | Almost always (late-stage) |
| DoubleSide needed | Rarely | Almost always (walls) |
| Camera near | 0.1 is fine | Must be < 0.1 for interiors |

## Scale anchors (verify in Stage 2)

| Reference (interior/architectural) | Value |
|---|---|
| Standard door height | 2.1m |
| Standard door width | 0.9m |
| Dining chair seat height | 0.45m |
| Dining table top | 0.75m |
| Bar counter top | 1.05–1.15m |
| Standing eye height | 1.6m |
| Residential ceiling | 2.4–2.7m |
| Commercial ceiling | 3.0–4.5m |
| Stair riser | 0.17–0.19m |
| Stair tread depth | 0.25–0.30m |

| Reference (vehicles/machines) | Value |
|---|---|
| Car tire diameter | 0.6–0.7m |
| Sedan roof height | 1.4–1.5m |
| Door handle height | 0.9m |
| Wheelbase (sedan) | 2.6–2.9m |

Every PARAMS dimension must be plausible against these. Adapt the table to the object class.

## Layout mode checklist
- [ ] Gestalt sentence written and logged to napkin?
- [ ] Scene type classified (interior/exterior/hybrid)?
- [ ] Reference images searched if user didn't provide any?
- [ ] 3–8 major parts identified, bounding box estimated?
- [ ] Scale anchors listed for this object class?
- [ ] Fact sheet produced (confirmed/inferred/placeholder)?
- [ ] At least two orthographic ASCII views drawn?
- [ ] Cross-view consistency table checked (Y/X/Z ranges match)?
- [ ] Surface alignment declared for every touching pair (which surface → which surface)?
- [ ] Spatial walkthrough written with body-relative language?
- [ ] PNG plan/elevation generated (if visualize.py available)?
- [ ] PARAMS schema centralized, stacking math shown explicitly?
- [ ] Material zones assigned (no adjacent surfaces share same material)?
- [ ] Detail tiers assigned (hero/mid/far)?
- [ ] Napkin updated with current state?

## Patch mode checklist
- [ ] Read the napkin first?
- [ ] Which PARAMS values change?
- [ ] Which builder functions read them?
- [ ] What cascades and what stays untouched?
- [ ] Is this truly local, or does it disturb circulation/anchors/silhouette (→ back to layout mode)?
- [ ] Regenerated only the relevant verification artifact?
- [ ] Paused with: Changed / Preserved / Cascade / What to review?
- [ ] Updated napkin with new values and reasons?

## Mid-flight mode escape protocol

Sometimes you discover mid-conversation that you're in the wrong mode. Don't continue — switch cleanly.

| Symptom | You're in | Switch to | How |
|---------|-----------|-----------|-----|
| "This needs more objects than I planned" | Layout | Narrative | Pause. Decompose to templates first. Resume layout for hero objects only. |
| "The whole layout feels wrong, not just one part" | Patch | Layout | Declare: "This exceeds patch scope." Log reason to worklog. Re-enter layout at Stage 3 (diagrams). |
| "I'm placing 10 similar objects by hand" | Layout | Narrative | Stop. Define template. Use placement rules. Return to layout for detail if needed. |
| "I don't know what this should look like yet" | Layout | Narrative N1 | Back to one-sentence description. Decompose before planning. |
| "The blockout is approved but one template needs detail" | Narrative | Layout | Enter layout mode for that template only. Don't re-plan the whole scene. |
| "The template is fine but it's in the wrong place" | Layout | Patch | Switch to patch. Trace the PARAMS change, apply, validate. |

**The protocol:**
1. Say "switching from [current mode] to [new mode] because [reason]"
2. Log the switch to `worklog.py`: `python scripts/worklog.py add MODE_SWITCH "patch→layout: whole layout unbalanced"`
3. Update the napkin with what's decided vs. what needs re-evaluation
4. Enter the new mode at the appropriate stage — don't restart from scratch

**Never silently drift between modes.** An undeclared mode switch is the most common source of compounding errors.

## ASCII diagramming rules
- State scale: `1 char ≈ 1m`
- Label both axes with name and unit ticks
- Mark origin with `+`, symmetry with `|` or `---`
- Label parts by name, repeated elements with `[×N]` count
- Characters: `#` solid, `|` `---` edges, `.` curves, `( )` domes/arches, `~` ground
- Choose scale so tallest dimension fits 15–25 rows, minimum width 30 chars
- No box-drawing Unicode, no perspective views

## Six named errors (check after every code pass)
1. **Y/Z swap:** "height" = Y, "depth" = Z, "width" = X. Always.
2. **Half-height clip:** `position.y = sum_below + ownHeight / 2`, not just `sum_below`.
3. **Invisible interior:** Enclosed spaces need DoubleSide or open top + interior light + camera near < 0.1.
4. **Uniform scale:** List 3 smallest and 3 largest objects — is the ratio plausible?
5. **Symmetric default:** At least 2 of 4 quadrants differ meaningfully (unless symmetry is intentional).
6. **Rotation axis mismatch:** `rotation.y` maps local +Z. If only SOME rotated instances look right, the atan2 formula aligns the wrong axis. To align local +Z with direction (dx, dz): `rotation.y = atan2(dx, dz)`.

## Critique order
1. Silhouette (thumbnail read)
2. Massing (proportions, weight)
3. Alignment (edges, center lines)
4. Depth (not a flat cutout)
5. Rhythm (part hierarchy, spacing)
6. Detail (too boxy / too noisy / too flat)

**Human review guidance to include:**
- Rotate 360°. Flickering? (Z-fighting)
- Back missing? (Facade-only)
- Shadow detached? (Floating geometry)

## Gestalt check
- [ ] Does the gestalt sentence still describe what's on screen?
- [ ] Does the mood match?
- [ ] Does the focal anchor read as the focal anchor?

## Consolidation check (every 3–4 refinement passes)
- [ ] Hardcoded numbers that should be in PARAMS?
- [ ] Functions over 40 lines that should be split?
- [ ] Stacking chain still clean?
- [ ] Naming consistent?

## Major pause template
```
### Decided
- [locked-in decisions]

### Uncertain
- [each uncertainty + assumption + alternatives]

### Next pass would...
- [what happens on "continue"]

### I need your input on:
- [specific questions]
```

## Handoff checklist
- Source-of-truth file and version name
- Project scope and current state
- Design philosophy
- What not to break (specific list)
- One focused next pass
- Require patch-plan-before-code
- Require screenshot review after pass

## Narrative mode checklist (v4 NEW)
- [ ] One-sentence scene written and logged to napkin?
- [ ] Decomposed to needs (count templates, not instances)?
- [ ] Needs list ≤ 6-8 items?
- [ ] Each template defined with minimum viable primitives?
- [ ] Footprint and bounding box on every template?
- [ ] Placement rules defined (not raw coordinates)?
- [ ] `spatial_validate.py` used for constraint-checked placement?
- [ ] Quick verify view generated (braille or ASCII top-down)?
- [ ] Human approved the blockout before proceeding?

## Braille verification checklist (v4 NEW)
- [ ] Braille views generated for at least 2 of 3 orthographic directions?
- [ ] Cross-view consistency checked (Y/X/Z ranges match)?
- [ ] Profile shapes compared against braille shape vocabulary?
- [ ] Complex curves described as piecewise segments, not equations?

## Draw-and-validate checklist (v4 NEW)
- [ ] Scene initialized with `spatial_validate.py init`?
- [ ] Every placement validated (no overrides on rejected placements)?
- [ ] Full scene check run after all placements (`check` command)?
- [ ] Spatial queries used for distance/overlap questions (not mental math)?
- [ ] Napkin updated with bounding boxes for every placed object?


## Verification stack (run in order)

1. **`spatial_validate.py check`** — overlaps, bounds, floating, zone violations. Fix all errors before proceeding.
2. **`braille_view.py front/side/top`** — silhouette, nothing floating, gross layout. ~20-40 tokens per view.
3. **`path_walk.py`** — walk the intended approach. Check for dead gaps, disconnected sequences, chokepoints. ~100 tokens for a full axis walk.
4. **Walk mode (scaffold, press F)** — human walks the scene at eye level. Catches composition and feel issues no tool can detect.

Do not skip step 1. Steps 2-3 are cheap and catch different things. Step 4 requires the human.

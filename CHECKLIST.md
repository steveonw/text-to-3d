# Checklist — what's done, what's left

A living document tracking the state of this skill. Update as pieces land.

**Legend:** ✅ done · 🟡 partial, usable · 🔴 stub, needs building · ⚪ nice-to-have, not blocking

---

## Tier 1 — Skill-defining pieces (blocking)

### ✅ Placement solver
The core spatial reasoner. Takes DSL in, returns placed pieces with coordinates.
- Location: `scripts/dropgrid/solver.py`
- Entry point: `scripts/dropgrid/api.py` → `solve_object_scene()`
- Status: working, ~410 lines, fast (~2ms for 46-piece scenes)

### ✅ DSL parser
Turns the compact object-description text into a structured scene spec.
- Location: `scripts/dropgrid/parser.py`
- Status: working, covers scatter/cluster/line/follow/rect_perimeter/rect_fill/circle/attach/center modes

### ✅ ASCII exporter
Cheap, token-efficient feedback channel for Claude to "see" the layout between passes.
- Location: `scripts/dropgrid/exporters.py`
- Status: working

### ✅ HTML scaffold with walk mode
Generates a standalone, openable `.html` file with orbit + first-person navigation.
- Location: `scripts/scaffold/scaffold_v4_walkmode.py`
- Status: working (ported from v4), has WASD + mouse + HUD + compass

### ✅ Per-piece context exporter
Given a placed piece, returns its local context — nearest neighbors, distances, facing direction, whether it's on an edge/interior/path, what zone it's in. Enables context-aware geometry authoring.
- Location: `scripts/authoring/context_exporter.py`
- Entry point: `export_all_contexts(scene_result)` → `{piece_id: context_dict}`
- Status: **working.** 229 lines, emits `interior`, `on_cluster_edge`, `in_corner`, `near_path`, `path_direction`, `outward_direction`, `neighbors`, `scene_center`.

### ✅ Geometry authoring protocol
A defined format for Claude to hand back geometry per piece, and a receiver that slots it into the scene. Schema: `{piece_id, primitives: [{shape, dimensions, position, rotation, material}]}`.
- Location: `scripts/authoring/geometry_receiver.py` + `scripts/authoring/schema.md`
- Entry point: `receive_all(packets)` → `{piece_id: validated_packet}`
- Status: **working.** Receiver with full validation (shape, dims, position, rotation, material/emissive). 62 tests pass.

### ✅ Renderer rewiring for LLM-authored geometry
Accepts authored geometry packets and assembles them into a complete Three.js scene positioned according to solver coordinates.
- Location: `scripts/scaffold/scaffold_v4_walkmode.py`
- Entry point: `generate_scene_html(scene_result, packets)` → HTML string
- Status: **working.** `build_body_from_packets()` generates per-piece Groups; missing packets get grey placeholder boxes.

### 🟡 SKILL.md philosophy refinement
SKILL.md captures the toddler-with-blocks philosophy and the full workflow. One round of iteration done.
- Location: `SKILL.md` (root of skill)
- Status: **first iteration done.** Needs eval runs against fresh Claude sessions and tightening where template-library thinking creeps back in. Ongoing.

---

## Tier 2 — Important supporting pieces

### ✅ Braille silhouette verifier
Cheap visual-ish check without burning tokens on an image.
- Location: `scripts/verification/braille_view.py` (ported from v4)
- Status: working

### ✅ Path walk verifier
Text-based simulated walkthrough — catches spacing issues, dead zones, unreachable spots.
- Location: `scripts/verification/path_walk.py` (ported from v4)
- Status: working

### ✅ Spatial validator
Overlaps, bounds, floating-object checks.
- Location: `scripts/verification/spatial_validate.py` (ported from v4)
- Status: working

### ✅ Teaching references (most of them)
Reference docs Claude loads on demand.
- Done: threejs-conventions, braille-spatial, checklists, narrative-decomposition, script-recipes
- All ported from v4, relevant to this skill

### ✅ Authoring guide reference
How-to for context-aware geometry authoring. Teaches the craft of improvising good-looking blocks in context.
- Location: `references/authoring_guide.md`
- Status: **done.** 315 lines covering context reading, coordinate conventions, primitive vocabulary, contextual variation (edge/interior/near_path/corner), scale discipline, materials, anti-patterns, and pre-submission checklist.

### ✅ DSL reference (distilled)
A focused DSL reference, not spread across multiple source READMEs.
- Location: `references/dsl_reference.md`
- Status: **done.** 305 lines covering all placement modes, anchor syntax, object fields, and worked examples.

### 🟡 Philosophy writeup
The full "toddler with blocks" philosophy as its own reference, separate from the SKILL.md intro.
- Location: `references/philosophy.md`
- Status: **partial.** 91 lines, core concepts written. Could use more examples of over-reuse vs. healthy variation.

### ✅ Full-loop worked example
Prompt → decomposition → DSL → solver output → per-piece authoring with context → verification → final HTML.
- Location: `references/worked_examples/full_loop_example.md`
- Status: **done.** 8-step trace on shrine clearing (23 pieces). Includes real ASCII layout, context packets for representative pieces, authored geometry with context-driven notes.

### 🟡 Verifier integration
Braille view, path walk, and spatial validator work in isolation but don't accept `SceneResult` directly.
- `braille_view.py` expects `parts` format (`x, z` centered, `w/d/h`)
- `spatial_validate.py` / `layout_compare.py` expect `items` format (`x, z` corner-positioned)
- `SceneResult.to_layout(fmt)` adapter added (see models.py) — unblocks all verifiers.
- `scene_inventory.py` works directly on rendered HTML — no glue needed.
- Status: **adapter added.** Needs integration test to confirm verifier workflows end-to-end.

### ✅ Try Now demo server
Local HTTP server that lets anyone run the full pipeline in a browser without installing anything.
- Location: `try_now.py`
- Status: **done.** GET `/` serves landing page with built-in examples + custom DSL textarea. POST `/generate` runs `solve_object_scene()` + `render_html()` and returns HTML to embed in an iframe. Three.js served locally from `vendor/` (no CDN required).

### ✅ Wall box-drawing chars as single source of truth
Box-drawing connectivity chars (─ │ ┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼ + caps) computed once in Python from actual neighbour positions and stored in `piece.meta['wall_sym']`. Both ASCII exporter and 3D renderer read from this — eliminates the orientation-divergence gap.
- Location: `scripts/dropgrid/exporters.py` → `annotate_wall_symbols()`, `_piece_wall_char()`
- Status: **done.** Handles multi-cell footprints (e.g. 2×1 fence). Gate excluded from wall connectivity set (special topology semantics).

### ✅ Bug fixes: parser bounds + follow target matching
- Parser: bounds check on `heading` keyword no longer throws on edge input.
- Follow mode: `target` now matches `p.type`, `p.group`, or `p.label` (was type-only — broke `target walkway` when pieces were labelled `walkway_0`, `walkway_1`).
- Location: `scripts/dropgrid/solver.py`, `scripts/dropgrid/parser.py`

### ✅ Example 3D scenes
Hand-authored Three.js scenes demonstrating the full pipeline at different complexity levels.
- `examples/campsite_3d.html` — outdoor campsite, custom geometry per type (trees, campfire, lanterns, logs, rubble)
- `examples/tavern_interior.html` — indoor tavern, wall_sym-driven panel orientation, box-drawing borders
- `examples/fishing_dock.html` — lake dock scene, water/shore split, rowboats, crab traps, reed stalks, shack
- `examples/workshop_interior.html` — workshop interior, cast-iron stove, workbench+vise, tool pegs, dusk window
- Status: **done.** All four committed. Color variation uses per-channel `vc()` function (no byte-overflow artifacts).

### ✅ Vendored Three.js
Local Three.js r128 build so scenes work offline and in environments where CDN is blocked.
- Location: `vendor/three.r128.min.js`
- Status: **done.** Served by `try_now.py` at `/vendor/three.r128.min.js`; also inlined in standalone example HTMLs.

---

## Tier 3 — Nice-to-have

### ⚪ Topology candidate integration
The 19-tests dropgrid had a more sophisticated topology system (rect perimeters with true openings, socket-based attachment, authoritative topology slots). It's parked at `scripts/dropgrid/topology_candidate/`. Integrating it would improve placement quality for architectural scenes.
- Status: code present but not wired in. Not urgent — current solver handles most cases.

### ⚪ Zones
DSL extension for naming regions ("kitchen area," "courtyard," "garden") and placing objects relative to zones rather than just other objects. Useful for interior scenes especially.
- Status: not started. Could be added as DSL extension + solver support.

### ⚪ Scale grounding
Commit to a real-world unit for grid cells (e.g. 1 cell = 1 meter) so chairs-are-1×1 and tables-are-2×1 decisions can be made with real proportions.
- Status: not started. Affects footprints.py and DSL docs.

### ⚪ Incremental re-solving / piece pinning
"Keep these pieces, re-roll the rest." Currently every solve is from scratch.
- Status: not started. Would need solver API changes.

### ⚪ Starter authoring snippets
Reference examples showing *how* to author specific kinds of blocks in context — not a library of geometries to reuse, but teaching examples. Deliberately not a template library.
- Status: not started.

### ⚪ Test coverage for new pieces
Once authoring protocol and context exporter are built, they need tests.
- Status: pending those pieces landing.

---

## What's deliberately excluded

These look like they're missing, but they're not — they contradict the skill's philosophy.

- **Template library** (v4 had one — `template_library.py`, `starter_library.json`). Not ported. Using it would violate the toddler-with-blocks principle.
- **Canonical object definitions.** Same reason.
- **Cross-session geometry caching.** Each scene is hand-made; there's nothing to persist.

If a future Claude reads this and thinks "let me just add a small library for common objects" — no. That's the failure mode this skill exists to avoid.

---

## Suggested build order

If picking up this work in Claude Code:

1. **Context exporter first.** Smallest, cleanest piece. Unblocks the authoring guide.
2. **Authoring protocol / geometry receiver.** Design the schema carefully — this is the skill's load-bearing data structure.
3. **Renderer rewiring.** Takes solver output + authored pieces → HTML. Surgery on existing scaffold code.
4. **Full-loop worked example.** Now possible because the pieces exist.
5. **Authoring guide reference.** Now possible because the protocol is concrete.
6. **SKILL.md iteration.** Test against real prompts, tighten the prose.

Then tier 3 as taste dictates.

---

## Notes for future Claude reading this

You will be tempted to add a template library. Resist. Read `references/philosophy.md` to re-ground.

You will be tempted to solve placement yourself instead of writing DSL. Resist. The solver is there so your attention stays on appearance.

When in doubt about what "toddler with blocks" means in practice: imagine a kid making the same scene twice. Would the two attempts look identical? If yes, you're doing it wrong.

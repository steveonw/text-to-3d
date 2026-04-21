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

### 🔴 Per-piece context exporter
Given a placed piece, returns its local context — nearest neighbors, distances, facing direction, whether it's on an edge/interior/path, what zone it's in. Enables context-aware geometry authoring.
- Target location: `scripts/authoring/context_exporter.py`
- Status: **not built.** A placeholder stub exists. The solver already has this information internally — needs a function to walk the solver's output and emit per-piece context packets.
- Estimated effort: ~half a day.

### 🔴 Geometry authoring protocol
A defined format for Claude to hand back geometry per piece, and a receiver that slots it into the scene. Probably a JSON schema: `{piece_id, primitives: [{type: "box", dims: [x,y,z], position: [x,y,z], rotation: [...], material: {...}}, ...]}`.
- Target location: `scripts/authoring/geometry_receiver.py` + schema doc
- Status: **not built.** Design decisions pending — see `scripts/authoring/README.md`.
- Estimated effort: ~1 day (schema + receiver + tests).

### 🔴 Renderer rewiring for LLM-authored geometry
The current `drop_grid_v6.html` renderer has baked per-type geometry. Needs a code path that accepts authored pieces from step above and assembles them into the scene, positioned according to solver coordinates.
- Target location: modified `scripts/scaffold/scaffold_v4_walkmode.py` + possibly a new HTML template
- Status: **not built.** Existing renderers still work, but they use the old baked-geometry approach.
- Estimated effort: ~1-2 days.

### 🔴 SKILL.md philosophy refinement
The draft SKILL.md captures the toddler-with-blocks philosophy, but it hasn't been tested with fresh Claude sessions. Expect iteration — behavioral shaping through prose is hard, and the LLM default is to reach for template-library thinking. Tightening the wording will be ongoing.
- Location: `SKILL.md` (root of skill)
- Status: **draft only.** Needs eval runs against real prompts, observation of where Claude falls back to template patterns, and corresponding prose tightening.
- Estimated effort: ongoing — probably a week of iteration across test scenes.

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

### 🔴 Authoring guide reference
How-to for context-aware geometry authoring. The piece that teaches Claude the actual *craft* of improvising good-looking blocks in context.
- Target location: `references/authoring_guide.md`
- Status: **not built.** Needs to be written once the authoring protocol exists, since it'll reference the protocol's data structures.

### 🔴 DSL reference (distilled)
A focused DSL reference, not spread across multiple source READMEs.
- Target location: `references/dsl_reference.md`
- Status: **stubbed** (draft exists). Needs to be written as a single authoritative reference drawing from dropgrid_complete's README, the parser source, and example DSL files.

### 🔴 Philosophy writeup
The full "toddler with blocks" philosophy as its own reference, separate from the SKILL.md intro.
- Target location: `references/philosophy.md`
- Status: **stubbed** (draft exists). Expand with examples of what counts as over-reuse vs. healthy variation.

### 🔴 Full-loop worked example
Existing worked examples (`gate_torches`, `topology_rect_demo`, `example-village`) show the placement half. Need one that shows the full loop: prompt → decomposition → DSL → solver output → per-piece authoring with context → verification → final HTML.
- Target location: `references/worked_examples/full_loop_example.md`
- Status: **not built.** Blocked on authoring protocol existing — can't write a worked example of something not yet designed.

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

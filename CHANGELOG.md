# Changelog

## v5 — May 2026

The v5 cut closes the verifier integration gap, adds the cross-piece narrative
layer past per-piece authoring, and tightens documentation around what's now
shipping vs. parked. No breaking API changes.

### Fixed

- **Scene now centers on world origin instead of sitting at the corner of the
  ground plane.** Pieces with raw dropgrid coords (e.g. `gx=15, gz=15`)
  previously emitted at world position `(15, 0, 15)` while the ground plane
  was a square centered at `(0, 0, 0)` — visually, the entire scene appeared
  offset toward one corner of the ground, with empty ground stretching away
  in the other directions.
  - **Fix:** `build_body_from_packets()` now accepts a `centroid` parameter;
    `generate_scene_html()` computes the scene centroid from piece positions
    and passes it through. Each piece's emitted `pg.position.set(x, y, z)`
    subtracts the centroid, so the scene's spatial center sits at world
    origin. Camera and orbit target are repositioned in the centered space.
  - **Backward compatibility:** `build_body_from_packets()`'s `centroid`
    parameter defaults to `(0, 0, 0)` — direct callers of that lower-level
    function get the old behavior unless they opt in.

- **`SceneResult.to_layout(fmt)` now returns the full layout dict** the v4 verifiers
  expect, not a flat list. Includes:
  - `room` dict with `width` / `depth` / `height`, computed from piece extent + padding
  - `parts` (centered x/z) or `items` (corner x/z + centered y) — pick by `fmt` arg
  - Per-type default bboxes (campfire, tree, lantern, fence, log, etc.) so
    single-cell pieces render at sensible sizes
  - Multi-cell pieces (fences, walls) use their actual `p.cells` extent
  - **Before:** `r.to_layout('parts')` returned `[{...}, ...]`; piping into
    `braille_view.render_top()` raised `'list' has no attribute 'get'`.
  - **After:** `r.to_layout('parts')` returns `{'room': {...}, 'parts': [...]}`;
    braille_view consumes it directly and renders the actual scene silhouette.

### Added

- **`scripts/verification/run_all.py`** — convenience runner that takes a
  `SceneResult` and produces a single report dict with the dropgrid ASCII
  view, braille silhouette, piece inventory, and basic spatial sanity
  warnings. CLI usage: `python scripts/verification/run_all.py --example shrine`.

- **`references/cross_piece_narrative.md`** — new reference for the "feels
  inhabited" layer past per-piece authoring. Three categories of detail:
  connectors between pieces, use-evidence props (kettle, mug, boots), and
  surface variation (chips, lichen, cracks). Where to insert each in the
  pipeline (in-packet vs extra DSL piece). Worked example of turning a
  sterile campsite into an inhabited one with ~7 small primitives.

### Changed

- **`SKILL.md`** — verification step (5) now points at `run_all.py` as the
  easiest path; explicitly notes `result.to_layout('parts'|'items')` as the
  glue. Key references table now includes `cross_piece_narrative.md`.

- **`CHECKLIST.md`** — verifier integration moved from 🟡 partial to ✅ done;
  cross-piece narrative reference added as a new ✅ Tier 2 item.

- **`references/authoring_guide.md`** — see-also section deduplicated and
  pointed at the new cross-piece narrative doc.

### Still open (intentionally)

- **DSL terminus pinning** — `from A to B` for paths that connect two named
  pieces, instead of just `from A heading X steps N`. Tracked as a Tier 3
  improvement; would close the "path-to-nowhere" failure mode at the layout
  level.
- **Anchored cluster placement** — orphan-prone objects like supplies should
  be authorable as "clusters around named anchor" rather than `radius N from
  center`. Related to the parked topology_candidate solver.
- **Scale grounding** — committing to "1 cell = 1 meter" across DSL,
  footprints, and authoring guide. Currently implicit.

These are documented and parked, not lost. See `CHECKLIST.md` Tier 3.

### Migration notes from v4 / pre-v5

- `result.to_layout(fmt)` callers that read `[{...}, ...]` will break. They
  now need to read `result.to_layout(fmt)['parts']` (or `['items']`). This is
  the only intentional shape change in v5; consumers using the dropgrid API
  directly are unaffected.
- All existing example scenes (`campsite_3d.html`, `tavern_interior.html`,
  `fishing_dock.html`, `workshop_interior.html`) continue to render
  unchanged.
- The geometry packet schema is unchanged. Authored scenes from v4 work
  against the v5 scaffold without modification.

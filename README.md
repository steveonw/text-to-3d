# text-to-3d-scene

A Claude skill for turning plain-English scene descriptions into walkable 3D HTML files — *without* a template library. Each object's geometry is authored fresh per scene.

```
"A forest shrine deep in the woods"
  → Claude decomposes the description
  → writes a small DSL
  → solver places 46 pieces (~2ms)
  → Claude authors geometry for each piece in its local context
  → HTML file you open in a browser and walk through
```

## Status

**Under active construction.** See `CHECKLIST.md` for what works and what's stubbed. The placement engine, verifiers, and HTML scaffold all work. The per-piece authoring protocol — the thing that makes this a handcrafted-scene skill rather than a template-library skill — is the main gap.

You can use the skill today for placement-driven scenes with baked geometry. You cannot yet use it for the full toddler-with-blocks vision.

## Philosophy in one line

The solver owns placement; Claude owns appearance; nothing gets cached into a library.

See `SKILL.md` for the full version, `references/philosophy.md` for the extended writeup.

## Quick map of the folder

```
SKILL.md                     # Teaching document Claude reads on load
CHECKLIST.md                 # What's done, what's left (inventory)
CLAUDE_CODE_CHEATSHEET.md    # Step-by-step build handoff for Claude Code
README.md                    # You are here

scripts/
  dropgrid_run.py        # Main entry point — solves a scene to HTML/ASCII
  dropgrid/              # Core placement engine
    topology_candidate/  # More sophisticated solver, parked for future integration
  verification/          # Braille, path walk, spatial validator
  scaffold/              # HTML generation (walk mode included)
  authoring/             # TODO — per-piece context + geometry protocol
  helpers/               # Workflow tools from v4 (napkin, worklog, visualize, etc.)

references/              # Docs Claude loads on demand
  threejs-conventions.md # Geometry primitives and patterns
  braille-spatial.md     # Reading verifier output
  checklists.md          # What to look for in verification
  narrative-decomposition.md
  script-recipes.md
  worked_examples/       # End-to-end traces

examples/                # Pre-rendered reference scenes
tests/                   # pytest suite
assets/                  # Icon
```

## Credits / provenance

This skill combines work from three source projects:

- **dropgrid_complete** — placement engine, DSL, parser, ASCII exporter, end-to-end pipeline
- **dropgrid (19-tests version)** — topology system (parked for integration), additional worked examples, tests
- **staged-3d-modeler-v4** — verifiers (braille, path walk, spatial), HTML scaffold with walk mode, teaching references, helpers

Template-library components from v4 (`template_library.py`, `starter_library.json`) were deliberately excluded — they contradict this skill's philosophy.

## Running tests

```bash
cd tests/
pytest
```

Some tests may need path adjustments since files have been reorganized. See `CHECKLIST.md`.

## If you're Claude loading this skill (to use it)

Read `SKILL.md` first. Then `CHECKLIST.md` to know what's real and what's stubbed. Then load references on demand as the user's request requires.

Resist the urge to build a template library. That's the failure mode this skill exists to avoid.

## If you're Claude Code picking up the build

Read `CLAUDE_CODE_CHEATSHEET.md` first. It has the orientation steps, the build order, the design questions that need human input, and the anti-patterns to watch for. Don't start coding until you've done the first-session orientation it describes.

# scripts/authoring/ — TODO

This folder holds the **per-piece authoring protocol** — the part of the skill that lets Claude supply geometry per piece, in context, rather than using baked-in geometry from the renderer.

It is the most important missing piece of this skill. Without it, this skill falls back to the dropgrid_complete behavior: decent placement with generic per-type geometry. That's not what we're building.

## What belongs here

### context_exporter.py (not built)

Takes the solver's output (list of placed pieces) and produces a per-piece context packet. For piece #N, the packet describes:

- Its own position, type, label, roles
- Its N nearest neighbors (type, distance, direction)
- What it's near (any piece within some threshold)
- What it's inside/outside (if zones exist)
- Whether it's on a path, on an edge, in an interior, in a corner
- What direction is "away from the center" from its position
- Any facing information from the DSL

The solver already knows all of this internally — it just doesn't export it. This module walks the solver's output and emits packets.

**Proposed signature:**

```python
def export_piece_context(piece, scene_result, neighbors=5) -> dict:
    """Return a context packet for a single piece."""

def export_all_contexts(scene_result, neighbors=5) -> dict[int, dict]:
    """Return contexts for every piece, keyed by piece id."""
```

### geometry_receiver.py (not built)

Accepts LLM-authored geometry per piece and prepares it for the scaffold. Defines the schema Claude writes to.

**Proposed schema** (JSON per piece):

```json
{
  "piece_id": 7,
  "primitives": [
    {
      "shape": "cylinder",
      "dimensions": [0.2, 0.2, 1.5],
      "position": [0, 0.75, 0],
      "rotation": [0, 0, 0],
      "material": {"color": "#4a3520", "roughness": 0.9}
    },
    {
      "shape": "cone",
      "dimensions": [0.8, 0.8, 1.2],
      "position": [0, 1.8, 0],
      "rotation": [0.1, 0, 0],
      "material": {"color": "#2d5028", "roughness": 0.7}
    }
  ]
}
```

Positions are **relative to the piece's own footprint center**, not world coordinates. The scaffold handles world positioning using the solver's piece coordinates; the authoring protocol just describes local geometry.

Supported primitives at minimum: `box`, `cylinder`, `cone`, `sphere`, `plane`.

### A small schema doc

Probably `schema.md` in this folder, describing the authoring packet format in detail so future Claude sessions can produce valid output without reading the receiver source.

## Design decisions that still need making

1. **Coordinate frame.** Local to footprint, or local to piece center? (Suggestion: footprint-local, origin at floor of cell, y-up.)

2. **Material vocabulary.** How rich should the material spec be? Full PBR (roughness, metalness, etc.) or simpler (color + rough/smooth)?

3. **Hierarchy.** Can primitives be grouped? (Useful for "this subassembly rotates together.") Probably yes, but adds schema complexity.

4. **Validation.** Should geometry_receiver.py validate incoming packets against the schema and reject malformed ones, or just pass them through and let the renderer fail?

5. **Fallback.** If Claude doesn't author a piece, what happens? Fall back to baked geometry? Render a placeholder cube? Warn?

6. **Batch vs streaming.** Does Claude author all pieces at once, or piece-by-piece with a tool call loop? (Affects how the skill's workflow documents tell Claude to work.)

These need to be decided before writing the receiver. Prototype in a Claude Code session; don't just commit to one.

## Why this matters

Without this module, the skill is *structurally* a template-library skill — even if the SKILL.md tells Claude not to think that way, the renderer has geometry baked in, so whatever Claude "decides" is overridden by what the renderer shows.

With this module, the skill becomes what it's meant to be: Claude's per-piece decisions actually appear in the output.

## Pointers

- Read `/references/philosophy.md` before designing the protocol. The design should make the philosophy easy to follow and hard to violate.
- Read `/references/threejs-conventions.md` for the primitive vocabulary Three.js offers.
- Look at `/scripts/scaffold/scaffold_v4_walkmode.py` — whatever schema you pick, the scaffold has to consume it.
- Look at `/scripts/dropgrid/models.py` — piece data structures you're extending.

## Status as of skill creation

Nothing here yet except this README and the two `.TODO` placeholder files. Build in the order suggested in `/CHECKLIST.md`.

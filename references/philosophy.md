# Philosophy — Toddler with Blocks

The operating principle of this skill, at length.

## The core image

A toddler builds a house from blocks. They don't look up "house" in a catalog. They grab blocks, stand them up, and declare *"this is a house."* Somebody else might grab different blocks, arrange them differently, and also declare *"this is a house."* Both are correct. The identity comes from the act of naming, not from matching a canonical schema.

Do that.

## What this rules out

**No template library.** Do not define a reusable "tree" or "chair" or "house" object that gets instanced many times. Do not build up a persistent catalog of geometries across sessions. Do not think "I'll define this well now and save effort later."

**No cross-piece reuse within a scene.** Even within a single scene, if you place 12 trees, author 12 different trees. Not "tree-with-tilt-variation-A applied 12 times with different rotations." Twelve authoring decisions.

**No cross-session caching.** If this skill worked on a tavern last week and works on one today, the chairs should not look the same. Start from scratch.

## What this asks for instead

Each piece is a small creative decision. When you're placing piece #7 — say, a tree at (9, 3), near the path, on the east side of the clearing — you make a little authoring choice: *this tree is two cylinders and a cone, the cone tilts slightly west because the tree is on the windward side, and it's a bit scruffier because it's near the path where people might brush past it.*

Next tree, different choice. Maybe three cylinders stacked, no tilt, because that one's sheltered by its neighbors.

None of these choices is big. Each one takes a few seconds of thought. The cumulative effect is what makes the scene feel made rather than assembled.

## Why this matters

### Variation at the right level

Three kinds of generation produce three kinds of output:

**Full-mesh generation** (one model producing the whole scene as a baked mesh): varies everything at once. You can't pick "vary the trees but keep the path." You get whatever the model produces, frozen.

**Template libraries** (define objects once, stamp them many times): vary nothing within a type. All trees are the same tree. Consistent, but dead — a medieval village where every house is identical doesn't feel like a village, it feels like a render test.

**Toddler-with-blocks** (solver places, LLM authors each piece fresh): varies the objects while keeping the composition principled. Twelve trees form a ring, but each tree is its own little sketch. The ring is solid; the trees breathe.

Real handcrafted worlds — a village someone built, a garden someone laid out — have this property. Every house is clearly a house. No two houses are identical. The layout has intent. The objects have individuality.

### Attention goes to the right place

LLMs are genuinely good at "improvise a small thing in context." They are genuinely bad at "hold a 46-piece spatial layout in your head and not lose track of coordinates."

This skill splits the work along that seam:

- **Solver**: holds the layout. Deterministic, fast, never miscounts, never loses a piece.
- **LLM**: improvises appearance. Only ever thinks about one piece at a time, with its local context.

Neither side is asked to do what it's bad at. The LLM's entire attention budget goes to small authoring decisions — which is where LLMs shine. The solver handles the bookkeeping — which is where solvers shine.

### Context-aware craft

The quiet payoff of this approach is that each piece can *react to its neighbors*. A tree near the path looks different from a tree deep in the forest. A chair at the head of a table can be slightly grander. A torch on a corner of the wall can be tilted a bit toward the courtyard.

None of this requires new templates. It just requires the LLM, when authoring each piece, to see what's around it and make a small contextual choice. That's what the per-piece context exporter exists for (see `scripts/authoring/` once built).

This is impossible with a template library — the template doesn't know where it's being stamped. It's trivial with per-piece authoring.

## Telltales that you're violating the philosophy

Some signs something has gone wrong:

- You're naming variables like `chair_template` or `tree_definition`.
- You're copy-pasting geometry code between pieces.
- You're thinking "if I get this one right, I can reuse it."
- The resulting scene has a "render test" feel — things look too regular, too stamped, too uniform in type.
- Two scenes built from different prompts have chairs that look identical.
- You made a file called `library.json` or `templates.py`.

If any of these are happening, re-ground here.

## What the philosophy does *not* say

**It does not say every piece must be maximally weird.** A handcrafted scene isn't chaotic. Trees in a ring are still all recognizably trees. Chairs at a table are still recognizably chairs. Variation happens within a clear idea, not instead of one.

**It does not say reject all reuse of concepts.** You can and should reuse patterns — "stacked cylinders make tree trunks" is a pattern, not a template. The difference: a pattern is a heuristic you adapt each time; a template is a geometry you stamp.

**It does not say ignore the user's request.** If the user says "I want ten identical chairs around this table," give them that. The philosophy is a default, not a dogma. Users can override.

**It does not say the LLM has to be slow or expensive.** Each per-piece authoring decision is small — a few primitives, a few seconds of thought. A 46-piece scene is 46 small decisions, not 46 long ones.

## The grounding question

When you're unsure whether you're following the philosophy or drifting from it, ask:

*"If I built this same scene again from scratch tomorrow, would the pieces look the same?"*

If yes — you're stamping. Author each piece fresh.

If no — you're handcrafting. Continue.

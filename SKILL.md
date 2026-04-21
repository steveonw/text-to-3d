---
name: text-to-3d-scene
description: Turn plain-English scene descriptions into walkable 3D environments rendered as standalone HTML files. Use this skill whenever the user asks to "build", "create", "generate", or "render" a 3D scene, environment, level, room, interior, village, compound, or any spatial composition they want to see and walk through — even if they don't say "3D" explicitly (e.g. "make me a medieval tavern", "design a shrine garden", "lay out a marketplace"). Unlike template-library approaches, this skill has Claude author each object's geometry fresh per scene — blocks arranged in context, not stamped from a catalog — while a Python solver handles placement.
---

# Text-to-3D Scene Skill

Build walkable 3D scenes from text descriptions. The solver handles *where* things go. You handle *what things look like* — fresh, every scene, every piece.

This skill is still **under construction**. Read `CHECKLIST.md` first to know what works and what's a stub. The philosophy and workflow below describe the target; some of the machinery to support it isn't built yet.

---

## The core philosophy

**You are a toddler with blocks.**

A toddler building a house doesn't look up "house" in a catalog. They grab blocks, stand them up, and declare *"this is a house."* Next time, different blocks, different arrangement, still a house. The identity comes from the act of making, not from a template.

That is the shape of this skill. **Do not build a template library.** Do not define a canonical "tree" and reuse it 50 times. Each piece is improvised in the moment, for this specific scene, considering what's around it.

Why this matters:

- **Variation is the point.** A scene where every chair is identical feels dead. A scene where each chair is hand-made, slightly different, feels alive.
- **Context should shape appearance.** A tree next to the path looks different from a tree in deep forest. The third chair in a row can be slightly scruffier than the first two. These micro-decisions are what make a scene feel handcrafted.
- **Your attention goes to appearance, not coordinates.** The solver places pieces. You don't have to track coordinates or avoid overlaps. Your whole creative budget goes to "what should this specific thing look like, here, next to these neighbors."

If you catch yourself thinking *"I defined a tree earlier, I'll reuse the same geometry,"* stop. Author a new tree. The variety is deliberate.

---

## The division of labor

| Responsibility | Who owns it |
|----------------|-------------|
| What does the user want? (decomposition) | You |
| Where does each piece go? (placement) | Solver |
| How does the solver know where to put things? (DSL) | You write it |
| What does piece #7 look like, specifically? | You (improvised) |
| Did the scene come out coherent? (verification) | Verifiers + you reading output |
| Final HTML assembly | Scaffold |

Notice: you do not own placement. If a placement feels wrong, **change the DSL and re-solve**. Do not try to override the solver's coordinates.

---

## The workflow

### 1. Decompose the request

User says: *"Build me a forest shrine."*

Think: what's in a forest shrine? A central altar or fountain. Trees around it in some arrangement. A path approaching it. Maybe lanterns along the path. Maybe stones or rubble as atmosphere.

Don't skip this step. A bad decomposition produces a bad DSL produces a bad scene.

### 2. Write the DSL

Compact, declarative. See `references/dsl_reference.md` for full syntax. Example:

```
anchor fountain shrine_center
ma hard radius 3

object tree label forest count 12 shape circle radius 7 clusters 4 spread 1
object road label path count 10 from shrine_center heading south steps 10 wobble 0.1
object lantern label lanterns count 5 target road side any distance 1 spacing 2
object rubble label clutter count 3 radius 10
```

The DSL is intentionally small. You can write a 46-piece scene in ~35 tokens of intent.

### 3. Run the solver

```bash
python scripts/dropgrid_run.py --scene my_scene.txt --output my_scene.html --ascii-only
```

The `--ascii-only` flag skips HTML generation on the first pass — you just want to see the layout. The solver returns an ASCII map showing piece positions.

### 4. Read the ASCII. Decide.

Look at the output. Did the trees form the ring you wanted? Is the path going the right direction? Are lanterns evenly spaced?

If yes → go to step 5. If no → **change the DSL and re-solve**. The solver is cheap (~2ms). Iterate freely.

### 5. Verify

Run cheap sanity checks before committing to a full render:

- **Braille view** (`scripts/verification/braille_view.py`) — a silhouette of the scene. Good for catching "wait, nothing should be over *there*."
- **Path walk** (`scripts/verification/path_walk.py`) — simulates walking through the scene as text. Catches dead zones, awkward spacing, unreachable areas.
- **Spatial validator** (`scripts/verification/spatial_validate.py`) — overlaps, out-of-bounds pieces, floating geometry.

See `references/checklists.md` for what to look for in verification output.

### 6. Author geometry per piece

**⚠ This step is partially stubbed. See `scripts/authoring/README.md`.**

For each placed piece, you supply the geometry — a small arrangement of Three.js primitives (boxes, cylinders, cones, spheres) that represents that specific piece. You see the piece's local context (neighbors, distances, what it's facing) and use it to shape the geometry.

Not "here is *the* tree." Here is *this tree, in this spot, with these neighbors.*

Read `references/threejs-conventions.md` for the primitive vocabulary and how to compose them. Read `references/authoring_guide.md` (TODO — not yet written) for the context-aware authoring approach.

### 7. Scaffold the HTML

```bash
python scripts/scaffold/scaffold_v4_walkmode.py [args]
```

Produces a standalone `.html` file with:
- Orbit camera for overview
- First-person walk mode (WASD + mouse, press F to toggle)
- HUD with position and compass
- No build step, no dependencies — opens in any browser

### 8. Iterate with the user

The user walks through it. They say "the lanterns are too close to the path" or "the trees feel sparse on the east side." You change the DSL and re-solve, or re-author specific pieces. Commit to nothing.

---

## When things go wrong

**The ASCII looks wrong.** Read `references/checklists.md`. Usually the DSL needs adjusting — wrong mode, wrong count, wrong relation. The solver doesn't invent; it does what you told it.

**Pieces overlap or float.** Spatial validator will catch this. Usually means the DSL asked for something impossible (e.g. too many objects inside a small region). Rethink counts or radii.

**The scene renders but feels "dead" or "AI-shaped."** You probably reused geometry across pieces. Each piece should be its own small authoring decision. If all your trees are the same three cylinders stacked, that's the warning sign.

**You want to add more of the same thing.** Fine — but *more* doesn't mean *identical*. Five market stalls should be five different arrangements of similar parts, not five copies of one arrangement.

---

## Working with existing scenes

The `examples/` folder has pre-rendered HTML scenes from the source projects (forest_shrine_v2, village_scene). **Look at them to understand what output is possible, but do not extract their geometry to reuse.** They were made by an older version of the pipeline that had baked-in per-type geometry. The skill you are building instead authors fresh.

---

## What's built, what's stubbed

Read **`CHECKLIST.md`** for a complete inventory. Summary:

**Working:** solver, DSL parser, verifiers (braille, path walk, spatial validate), HTML scaffold with walk mode, ASCII exporter.

**Stubbed:** per-piece context exporter, geometry authoring protocol, renderer rewiring to accept LLM-authored geometry, full end-to-end worked example.

If a user asks for a scene and the authoring pieces aren't built yet, you can still produce a valid scene using the baked-in geometry path in `dropgrid_run.py` — just be honest that it's not the handcrafted version. Or fall back to authoring by hand in the HTML if the user is okay with manual work.

---

## Key references

Load these when needed — don't try to read them all upfront.

| File | When to read it |
|------|-----------------|
| `references/philosophy.md` | Full writeup of the toddler-with-blocks principle |
| `references/dsl_reference.md` | Writing the scene description |
| `references/threejs-conventions.md` | Composing geometry from primitives |
| `references/braille-spatial.md` | Reading braille verifier output |
| `references/checklists.md` | Verification passes — what to look for |
| `references/narrative-decomposition.md` | Turning a user's description into a DSL |
| `references/script-recipes.md` | Common Three.js patterns |
| `references/worked_examples/` | End-to-end traces (placement only; full loop TODO) |

---

## Anti-patterns — things this skill explicitly rejects

- **Template libraries.** No canonical "chair," "tree," "house." Author each piece fresh.
- **Re-using geometry across pieces.** Even in the same scene, each piece is its own authoring decision.
- **Overriding the solver's coordinates.** If placement is wrong, change the DSL — don't patch positions after the fact.
- **Asking the LLM to hold a large spatial layout in its head.** That's the solver's job. The LLM's job is small, local, in-context authoring decisions.
- **Treating the DSL as final art.** It's the spec, not the scene. The scene emerges from solver + authoring + verification.

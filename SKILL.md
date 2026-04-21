---
name: text-to-3d-scene
description: Turn plain-English scene descriptions into walkable 3D environments rendered as standalone HTML files. Use this skill whenever the user asks to "build", "create", "generate", or "render" a 3D scene, environment, level, room, interior, village, compound, or any spatial composition they want to see and walk through — even if they don't say "3D" explicitly (e.g. "make me a medieval tavern", "design a shrine garden", "lay out a marketplace"). Unlike template-library approaches, this skill has Claude author each object's geometry fresh per scene — blocks arranged in context, not stamped from a catalog — while a Python solver handles placement.
---

# Text-to-3D Scene Skill

Build walkable 3D scenes from text descriptions. The solver handles *where* things go. You handle *what things look like* — fresh, every scene, every piece.

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

```python
import sys; sys.path.insert(0, "scripts")
from dropgrid.api import solve_object_scene

result = solve_object_scene(DSL, seed=42, debug=False)
print(result.to_ascii(include_legend=True))
```

The solver returns a `SceneResult` with every placed piece. `.to_ascii()` prints the grid so you can see the layout before committing to geometry authoring.

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

First, get the context packet for every piece:

```python
from authoring.context_exporter import export_all_contexts
contexts = export_all_contexts(result)
```

Each context packet tells you: is this piece on the edge or interior? Is it near a path? Which way is "outward"? Who are its nearest neighbors? Use this to shape the geometry.

For each piece, produce a geometry packet — a list of Three.js-style primitives in the piece's local coordinate space (y = 0 is the floor):

```python
packet = {
    "piece_id": 7,
    "primitives": [
        {
            "shape": "cylinder",
            "dimensions": [0.14, 0.18, 1.1],
            "position": [0.0, 0.55, 0.0],
            "rotation": [0.0, 0.0, 4.0],   # degrees
            "material": {"color": "#4a3218", "roughness": 0.9}
        },
        {
            "shape": "cone",
            "dimensions": [0.5, 1.1],
            "position": [-0.06, 1.65, 0.06],
            "rotation": [0.0, 0.0, 5.0],
            "material": {"color": "#2a5022", "roughness": 0.85}
        }
    ]
}
```

Then validate all packets at once:

```python
from authoring.geometry_receiver import receive_all
packets = receive_all([packet_1, packet_2, ...])   # raises GeometryError if any are invalid
```

Not "here is *the* tree." Here is *this tree, in this spot, with these neighbors.*

Read `references/authoring_guide.md` for the full context-aware authoring approach and `scripts/authoring/schema.md` for the packet format reference.

### 7. Assemble the HTML

```python
from scaffold.scaffold_v4_walkmode import generate_scene_html

html = generate_scene_html(result, packets, title="Forest Shrine")
with open("forest_shrine.html", "w") as f:
    f.write(html)
```

Produces a standalone `.html` file with:
- Orbit camera auto-framed to the scene
- First-person walk mode (WASD + mouse, press **F** to toggle)
- HUD with position and compass
- No build step, no dependencies — opens in any browser

Pieces without a geometry packet get a grey placeholder box, so partial authoring sessions still render.

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

The `examples/` folder has pre-rendered HTML scenes (`forest_shrine_v2`, `village_scene`). **Look at them to understand what output is possible, but do not extract their geometry to reuse.** They were made with baked-in per-type geometry — the approach this skill deliberately replaces. Study them for spatial composition, not for primitive arrangements.

---

## What's built

The full pipeline is operational:

| Module | Location | Status |
|--------|----------|--------|
| Placement solver | `scripts/dropgrid/api.py` | ✅ working |
| DSL parser | `scripts/dropgrid/parser.py` | ✅ working |
| ASCII exporter | `scripts/dropgrid/exporters.py` | ✅ working |
| Per-piece context exporter | `scripts/authoring/context_exporter.py` | ✅ working |
| Geometry packet receiver | `scripts/authoring/geometry_receiver.py` | ✅ working |
| HTML scaffold + walk mode | `scripts/scaffold/scaffold_v4_walkmode.py` | ✅ working |
| Scene HTML from packets | `generate_scene_html()` in scaffold | ✅ working |
| Verifiers (braille, path walk, spatial) | `scripts/verification/` | ✅ working |

Read `CHECKLIST.md` for tier 2/3 items and known gaps.

---

## Key references

Load these when needed — don't try to read them all upfront.

| File | When to read it |
|------|-----------------|
| `references/philosophy.md` | Full writeup of the toddler-with-blocks principle |
| `references/authoring_guide.md` | How to author context-aware geometry — the craft guide |
| `references/dsl_reference.md` | Writing the scene description |
| `references/threejs-conventions.md` | Composing geometry from primitives |
| `scripts/authoring/schema.md` | Geometry packet JSON schema |
| `references/braille-spatial.md` | Reading braille verifier output |
| `references/checklists.md` | Verification passes — what to look for |
| `references/narrative-decomposition.md` | Turning a user's description into a DSL |
| `references/script-recipes.md` | Common Three.js patterns |
| `references/worked_examples/full_loop_example.md` | Full end-to-end trace: DSL → solver → context → authored geometry → HTML |

---

## Anti-patterns — things this skill explicitly rejects

- **Template libraries.** No canonical "chair," "tree," "house." Author each piece fresh.
- **Re-using geometry across pieces.** Even in the same scene, each piece is its own authoring decision.
- **Overriding the solver's coordinates.** If placement is wrong, change the DSL — don't patch positions after the fact.
- **Asking the LLM to hold a large spatial layout in its head.** That's the solver's job. The LLM's job is small, local, in-context authoring decisions.
- **Treating the DSL as final art.** It's the spec, not the scene. The scene emerges from solver + authoring + verification.

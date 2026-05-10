# Cross-Piece Narrative — making scenes feel inhabited

> **When to read this:** After authoring per-piece geometry feels solid but the scene still reads as "objects placed correctly" rather than "a place where people live." This is the layer past silhouettes — the small details that imply *use*.

The authoring guide teaches how to make each piece read as its type with theme and variation. That's necessary, but not sufficient. A scene of correctly-authored pieces can still feel staged, because real places aren't just objects — they're objects that *connect* to each other through use.

**This guide covers the small connections.** The kettle near the firepit. The rope between two posts. The footprint-worn arc around the bench. A mug left on the table. None of these are pieces in the solver's sense; they're details that bridge between pieces and imply that someone uses this space.

---

## The "test fixture" smell

When you've authored 20 pieces by the per-piece guide and the scene still reads as a test fixture, the symptom is usually one of these:

- **Every piece sits exactly on the grid as if dropped from above.** Real objects shift, lean, settle. A barrel doesn't always sit perpendicular to the wall it's against.
- **Nothing connects to anything.** Two tents in a camp don't acknowledge each other — no rope between them, no shared mat, no path worn between their entrances.
- **Each object is immaculate.** Real wood is splintered. Real stone has lichen. Real fabric has wrinkles. Hand-authoring with one or two primitives per piece can't capture this directly, but tiny "flaw" primitives can hint at it.
- **No human-scale evidence.** No mug, no boot, no dropped scarf, no kettle. Without a human-scale prop, the eye has nothing to anchor scale against and the scene reads as a model rather than a place.
- **Symmetry where there shouldn't be.** Real camps are asymmetric. Real markets have one stall doing better than the others. If your campsite is perfectly four-fold symmetric, it reads procedural.

---

## Three categories of cross-piece detail

### 1. Connectors — explicit ties between pieces

These are small primitives whose purpose is to show that two pieces are related.

**Rope between posts.** A thin cylinder spanning two fence posts, sagging slightly. Add it as an extra piece in the DSL with mode `attach to fence_2 to fence_3`, or add it as a primitive in the second post's geometry packet.

**Shared mat / rug.** A thin flat box under a cluster of pieces (chairs around a table, a bedroll between two tent posts). Reads as "these belong together."

**Worn path between two pieces.** A faint dark stripe on the ground from frequent foot traffic. Two posts of a fence are connected by a slightly darker trampled line.

**Cable / chain / string of lights.** A series of small primitives running between two fixed points. Reads as deliberate human work.

### 2. Use-evidence — small props that imply someone was here

These are tiny primitives or extra small pieces sitting on/beside larger ones.

**Kettle by the fire.** A small dark cylinder + a thin handle arc. Can be authored as a primitive within the campfire piece's packet (`offset 0.6m east of the fire ring`).

**Mug on the table.** A small cylinder + handle. Tells the eye "someone was sitting here."

**Boot or sandal pair.** Two small dark forms near a tent entrance. Even at low fidelity, the eye reads "shoes" and infers a sleeper.

**Pot of water near a well / source.** Wide, shallow, dark — implies recent use.

**Tools leaning against walls.** A long thin cylinder leaning on a wall reads as "axe" or "rake" without needing the head.

**Drying laundry / sails / canvas.** A long horizontal flat box with slight droop, hung between two posts.

**Embers, ash, smoke trail.** A small grey-black flat patch beside the firepit.

### 3. Surface variation — the "not perfect" layer

Per-piece geometry tends to be clean. Real surfaces aren't.

**A small splinter / chip on a barrel.** One extra tiny dark primitive on the rim of an otherwise clean barrel.

**A rolled-down corner on a tent flap.** Slightly rotate one of the canopy primitives to read as "this side is open today."

**Lichen / moss on stones.** A tiny green-grey flat patch on the side of a rock facing away from sun.

**Cracks in path stones.** A thin dark line on every third path tile, varying angle.

**Scuff marks on the floor near doors.** A slightly darker patch where feet land.

These are *not* about modeling damage realistically. They're about giving the eye one or two points of "this isn't pristine" per piece, so the scene reads as lived-in rather than freshly-installed.

---

## Where these go in the pipeline

Cross-piece detail can live in two places:

### A. As primitives inside an existing piece's packet

When the detail belongs to a single piece — a kettle by the fire, a chip on a barrel, lichen on a rock — author it as one or two extra primitives in that piece's packet. The piece's packet is your local authoring decision; "the campfire piece includes a small kettle near it" is fine.

```python
# Inside author_campfire(piece, ctx):
prims.extend([
    # ... main fire primitives ...
    # kettle — small dark cylinder offset east of the fire
    {"shape": "cylinder", "dimensions": [0.18, 0.18, 0.22],
     "position": [0.6, 0.11, 0], "rotation": [0, 0, 0],
     "material": {"color": "#2a2418", "roughness": 0.7}},
    # kettle handle
    {"shape": "torus", "dimensions": [0.10, 0.015],
     "position": [0.6, 0.30, 0], "rotation": [0, 0, 90],
     "material": {"color": "#2a2418", "roughness": 0.7}},
])
```

### B. As extra DSL pieces

When the detail spans multiple pieces — a rope between two posts, a path worn between two tents — add it as its own DSL object. The solver places it; you author it like any other piece.

```
# In the DSL:
object rope label tent_rope count 1 from tent_2 to tent_3
object trampled label worn_arc count 6 attach to bench_1 side any distance 0.8 spacing 0.4
```

(Note: not all of these DSL modes exist as of this skill version. Adding "from A to B" termination and small-radius attach scatter to the DSL is on the roadmap. Until then, use approach (A).)

---

## When NOT to add cross-piece detail

This guide invites accumulation, but accumulation has a cost. Push back on cross-piece detail when:

- **The scene is meant to read as abandoned or new.** A pristine new shrine doesn't have lichen yet. An abandoned outpost doesn't have steaming kettles.
- **You're adding the same connector to every pair of pieces.** If every tent has a rope, no tent has a rope. The eye filters it out as background.
- **The detail breaks the silhouette of the main piece.** A kettle so big it visually competes with the campfire is wrong. The main piece should still read first.
- **You're at token budget.** Cross-piece detail is a luxury. If a scene has 50 pieces and you're running long, prioritize per-piece silhouette quality first; add cross-piece detail to the hero pieces only.

---

## Worked example — turning a sterile camp into an inhabited one

Before: campsite with 4 tents, 1 fire, 4 logs, 3 barrels. Each authored cleanly per the authoring guide. Reads as test fixtures.

After cross-piece pass — added details:

**Within campfire packet:** kettle (2 prims) + ash patch (1 prim) on the south-east side. Scene now has a "someone is cooking" cue.

**Within one tent packet (only — not all four):** a pair of small dark boots (2 prims) at the entrance. That tent is now "occupied"; the others read as empty by contrast, which is more interesting than four identically-occupied tents.

**Within one log packet:** a small mug (1 prim) on the seat. That log is now "the seat someone left."

**Within one barrel packet:** a coiled rope (1 torus) on top. That barrel is now storage, not just a barrel.

**Between two posts (extra DSL piece, 1 prim):** a thin cylinder spanning them at 1.5m — a clothesline.

Total added: ~7 small primitives across 6 pieces. The scene now reads as inhabited without any change to placement, layout, or per-piece silhouette quality.

---

## Quick checklist

Before calling a scene done, scan it for:

- [ ] Is there at least one human-scale prop (mug / boot / kettle / tool)?
- [ ] Does at least one piece show evidence of *recent* use (steam, ash, cracked door, dropped item)?
- [ ] Is there at least one connector between two pieces (rope, shared mat, worn path)?
- [ ] Are the pieces of one type *not* all in identical condition (one weathered, one fresh)?
- [ ] If the scene is a populated place, can you point to where the inhabitants would be sitting / sleeping / working?

A "no" to all five is a clean test fixture. A "yes" to two or three is usually enough to flip the scene from staged to lived-in.

---

## See also

- `references/authoring_guide.md` — per-piece silhouette and variation. Read this first.
- `references/philosophy.md` — why "lived-in" is the goal.
- `references/checklists.md` — broader verification passes.

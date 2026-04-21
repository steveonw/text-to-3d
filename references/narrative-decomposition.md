# Narrative Decomposition

## The principle

Don't start with geometry. Start with a sentence. Decompose by asking "what do I actually need?" Build from the simplest shapes that read correctly. Place with rules, not coordinates. Verify inline.

This is a pre-planning step that happens before the base skill's Stage 1. It catches complexity budget issues before they become planning debt.

## The pipeline

### Step 1: One-sentence scene

Describe the entire scene in one natural sentence.

> "A quiet village street with a row of small houses on each side of a road, a few people walking around."

This sentence contains all the spatial relationships. Don't overthink it.

### Step 2: Decompose to needs

Ask: **what distinct things do I actually need to build?**

Not "what's in the scene" but "what templates do I need." A row of 10 houses is one template, not 10 objects.

Write a needs list:
```
NEEDS:
1. ground — flat plane. Done.
2. road — strip down center. Done.
3. house — ONE template, repeat in rows.
   → randomize: color per instance
4. person — simple figure, scatter.
   → randomize: color per instance
```

**Four things. That's it.** If your needs list has more than 6-8 items for a typical scene, you're overbuilding.

### Step 3: Minimum viable primitives

For each need, define the simplest possible geometry that reads as that thing from camera distance.

Don't model detail. Model recognition. A person at street scale is a sphere on two cylinders. A house is a box with a cone on top. A tree is a cylinder with a sphere cluster.

```
house_template = {
  box(3, 2.5, 3)        → walls
  cone(2.5, 1.5, 4)     → roof
  box(0.6, 1.2, 0.1)    → door
  box(0.5, 0.5, 0.1)    → window
  footprint: 3×3
}

person_template = {
  sphere(0.18)           → head
  cylinder(0.2, 0.8)     → body
  cylinder(0.12, 0.5)    → legs
  footprint: 1×1
}
```

Count the primitives. A house is 4 meshes. A person is 3. Ten houses + 8 people = 64 meshes total. That's well within budget.

### Step 4: Placement rules (not coordinates)

Don't hand-place each object. Define rules:

```
PLACEMENT:
- houses: rows on each side of road
  spacing: ~3.5 units
  jitter: ±0.5 position, random color from palette
  
- people: scatter on walkable tiles
  REJECT IF: on road OR overlapping house footprint
  count: 6-10
```

The rules generate coordinates. The coordinates are a consequence, not an input.

### Step 5: Quick verify

Before entering the full skill pipeline, generate a braille or ASCII top-down view:

```
⌂ ⌂ ⌂ ⌂ ⌂ ░░░ ⌂ ⌂ ⌂ ⌂ ⌂
    ☺       ░░░     ☺
  ☺         ░░░         ☺
⌂ ⌂ ⌂ ⌂ ⌂ ░░░ ⌂ ⌂ ⌂ ⌂ ⌂
```

Does it read as a village street? Yes → proceed to full planning.
No → adjust rules, don't adjust coordinates.

## Template definition format

```json
{
  "id": "house_v1",
  "name": "Village House",
  "parts": [
    {"shape": "box", "w": 3, "h": 2.5, "d": 3, "material": "brick", "y_offset": 1.25},
    {"shape": "cone", "r": 2.5, "h": 1.5, "sides": 4, "material": "roof", "y_offset": 3.25},
    {"shape": "box", "w": 0.6, "h": 1.2, "d": 0.1, "material": "wood_dark", "y_offset": 0.6, "z_offset": 1.51},
    {"shape": "box", "w": 0.5, "h": 0.5, "d": 0.1, "material": "glass", "y_offset": 1.6, "z_offset": 1.51, "x_offset": 0.8}
  ],
  "footprint": [3, 3],
  "bounding_box": [3, 4.75, 3],
  "attachments": {
    "surface_top": {"y": 2.5, "area": [3, 3]},
    "door": {"face": "south", "y": 0, "w": 0.6, "h": 1.2}
  },
  "randomize": {
    "parts.0.color": ["#b85533", "#c46838", "#a84828", "#d4885a"]
  }
}
```

Key properties:
- **footprint**: 2D space this occupies on the placement grid
- **bounding_box**: 3D extents [x, y, z] for collision checking
- **attachments**: named points/surfaces for relational placement
- **randomize**: which properties vary per instance

## Instance placement format

Once templates are defined, scenes are just placement tables:

```
SCENE: village_street
GRID: 30×20
ROAD: center, width=3, axis=Z

PLACE house_v1 ROWS:
  side=west, count=5, spacing=3.5, offset_from_road=4
  side=east, count=5, spacing=3.5, offset_from_road=4

SCATTER person_v1:
  count=8
  REJECT: on_road OR overlap(house_v1, margin=1)
```

This entire scene description is ~150 bytes. A raw coordinate list for the same scene would be ~800+ bytes. The template-instance separation is an 80%+ compression.

## When to use narrative decomposition vs full planning

| Situation | Use |
|-----------|-----|
| New scene from scratch | Narrative decomposition → then full layout mode |
| Single hero object (cathedral, vehicle) | Skip narrative, go straight to layout mode |
| Scene with many repeated elements | Narrative decomposition — it'll catch the template pattern |
| "Make it feel like X" | Narrative first — capture the feeling, then decompose |
| Adding objects to existing scene | Template check — does a template exist? If not, build one, then place |

## Integration with base skill

After narrative decomposition, you enter the base skill at Stage 1 with:
- Gestalt sentence (from Step 1)
- Parts list with complexity budget (from Steps 2-3)
- Template definitions (from Step 3)
- Placement strategy (from Step 4)
- Quick verification that the concept reads (from Step 5)

This front-loads decisions that would otherwise emerge piecemeal during Stages 1-5 of the base workflow. The base stages then refine rather than discover.

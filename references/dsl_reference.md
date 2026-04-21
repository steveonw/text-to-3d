# DSL Reference

The scene description language the solver consumes. Small, declarative, token-efficient.

## At a glance

```
anchor <type> <label>            # Single center piece (optional)
ma hard radius <N>               # Protected void around anchor (optional)

object <type>
  label <name>
  count <N>
  roles <role1> <role2>          # Tags describing what the object does
  <placement-mode-directive>
  <relation-directive>
  importance <primary|secondary|background>
```

A scene is one anchor (optional) plus any number of `object` blocks.

## Placement modes

Each object block needs one placement directive. The parser dispatches on what you write.

### Motif: ring or rectangle around something

```
object tree label forest count 12 shape circle radius 7 clusters 6 spread 1
object fence label yard count 20 shape rectangle width 8 depth 6
```

- `shape circle radius N` — ring of pieces around the anchor
- `shape rectangle width N depth N` — rectangular perimeter
- `clusters N` — group pieces into clusters (optional)
- `spread N` — how far pieces can drift from the ideal (optional)

### Path: line from a point in a direction

```
object road label path count 14 from altar heading south steps 14 wobble 0.15
```

- `from <label>` — starting point (usually the anchor or a named piece)
- `heading <n|s|e|w|ne|nw|se|sw>` — direction
- `steps N` — how many pieces long
- `wobble N` — optional jitter, 0 = straight line

### Follow: attach to something else

```
object lantern label lanterns count 6 target road side any distance 1 spacing 2
object bench label pews count 4 target altar side east spacing 2
```

- `target <label>` — what to follow/attach to
- `side <left|right|any|north|south|east|west>` — which side
- `distance N` — how far off the target
- `spacing N` — gap between consecutive pieces

### Scatter: random placement in a region

```
object rubble label clutter count 3 radius 12
```

- `radius N` — scatter within N cells of the anchor
- Just `radius` with no other directives → scatter mode

### Perimeter with opening (from topology_candidate, advanced)

```
object fence label yard_edge mode rect_perimeter
object gate label front_gate target yard_edge socket opening facing south
```

- `mode rect_perimeter` — declares a topologically-owned perimeter
- `socket opening` — cut an opening in the target's perimeter
- `facing <direction>` — which side of the perimeter to cut

Note: this is from the topology candidate integration; requires the topology_candidate scripts to be wired in. Basic scenes don't need it.

### Center

```
object fountain label shrine_center inside yard_edge
```

- `inside <label>` — place this piece inside the region defined by target
- Resolves to the center of the target

## Relations

These modify any placement mode:

- `near <label>` — bias toward being close to another piece
- `inside <label>` — must be inside the region of another piece
- `outside <label>` — must be outside the region
- `around <label>` — encircle another piece
- `along <label>` — follow another piece's path/edge
- `facing <direction>` — orient toward a direction

## Roles and traits

Roles are semantic tags the solver may use for smarter placement:

```
roles barrier boundary
roles marker
roles gate_opening gate_frame
```

Not all roles do anything yet — they're there for future solver improvements. Safe to include for documentation.

Traits work the same way: `traits weathered decorative`.

## Importance

```
importance primary
importance secondary
importance background
```

Affects what the solver prioritizes when it has to compromise (e.g. dropping pieces if there's no room). Primary pieces get placed first.

## Comments

```
# This is a comment
object tree label forest count 12 ...
```

Lines starting with `#` are ignored.

## Dispatch rules — what you write vs. what the solver does

| You write | Solver does | Use for |
|-----------|-------------|---------|
| `shape circle` or `shape rectangle` | Motif emitter (ring, arc, clusters) | Things around something |
| `from X heading Y` | Path turtle | Roads, trails, walls |
| `target X` (no shape) | Follow/attach | Lanterns along road |
| `radius N` only | Scatter | Clutter, props |
| `mode rect_perimeter` | Topology-owned perimeter | Walled yards (advanced) |

**Any type can use any emitter.** Trees can be rings. Roads can be scattered. Lanterns can form rectangles. The intent controls placement; the type name is just a label.

## Full example: forest shrine

```
anchor fountain shrine_center
ma hard radius 3

object tree label forest count 12 shape circle radius 7 clusters 4 spread 1
object road label path count 10 from shrine_center heading south steps 10 wobble 0.1
object lantern label lanterns count 5 target path side any distance 1 spacing 2
object rubble label clutter count 3 radius 10
```

46 pieces total. ~35 tokens of intent.

## Full example: walled shrine with gate

```
anchor fountain shrine_center
ma hard radius 2

object fence label yard_edge roles barrier boundary mode rect_perimeter importance primary
object gate label front_gate roles gate_opening target yard_edge socket opening facing south importance primary
object torch label gate_torches count 2 roles marker target yard_edge socket face near front_gate
object rubble label clutter count 3 mode scatter inside yard_edge
object road label approach mode line target front_gate
```

Demonstrates topology mode. Requires topology_candidate integration.

## Tips for writing good DSL

- **Start with the anchor.** It's the spatial root. Everything else is placed relative to it.
- **Primary pieces first.** If the scene is overcrowded, `importance` decides what survives.
- **Small counts first.** Start with count=4 for a ring of trees; bump to 12 once the placement looks right.
- **Iterate the DSL, not the solver.** If pieces land wrong, change the DSL and re-solve. The solver is cheap.
- **One directive per object, usually.** Don't mix motif + path + follow on the same object. Pick one.

## When it goes wrong

**"Pieces are overlapping"** — usually too many pieces in too small a radius. Reduce count or increase radius.

**"Trees ended up on the path"** — the motif ring is bigger than the path length, or the wobble is too high. Tighten spacing.

**"Everything landed on the anchor"** — probably missing a placement directive. Every `object` block needs one of: `shape`, `from`, `target`, or `radius`.

**"The solver warned about a missing label"** — you referenced a label in `target` or `from` that doesn't exist. Check spelling; order doesn't matter (the parser resolves references after parsing all blocks).

## See also

- `scripts/dropgrid/parser.py` — authoritative source for what the parser accepts
- `references/worked_examples/` — traces of DSL through the whole pipeline
- `references/narrative-decomposition.md` — how to turn a user's prose description into DSL

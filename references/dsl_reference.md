# DSL Reference

The scene description language consumed by `solve_object_scene()`. Small, declarative,
token-efficient. A 40-piece scene fits in ~6 lines.

---

## Format

Every statement is a **single line**. Order matters for `target` and `to` — reference
a piece that was already declared in an earlier `object` line.

```
anchor <type> <label>
ma [hard] radius <N>

object <type> label <name> count <N> <placement-directive> [modifiers...]
object <type> label <name> count <N> <placement-directive> [modifiers...]
# comment lines are ignored
```

---

## The anchor

```
anchor campfire shrine_center
```

Exactly one anchor per scene. It is placed at the grid center. Everything else
is positioned relative to it. The anchor type is any valid piece type; the label
is how other lines refer to it.

---

## Movement area — `ma`

```
ma hard radius 5
```

Marks a circular void around the anchor. Pieces cannot be placed inside it.
Useful for keeping the anchor visible and preventing crowding around the focal point.

| Token | Meaning |
|---|---|
| `hard` | No pieces at all inside the zone (default) |
| `soft` | Prefer to avoid; may place if needed |
| `radius N` | Radius in grid cells |

Omit `ma` entirely to allow pieces right up to the anchor.

---

## Object statements

```
object <type> label <name> count <N> <placement-directive> [modifiers]
```

| Token | Type | Notes |
|---|---|---|
| `type` | string | Any word — `tree`, `road`, `lantern`, `barrel`, etc. Type name is a label; it doesn't constrain geometry |
| `label <name>` | string | How this group is referenced by later lines and in context packets |
| `count <N>` | int | Number of pieces to place |

Everything after `count` is one **placement directive** plus optional **modifiers**.

---

## Placement directives

There are four. The parser picks the mode by what keywords are present.

### 1. Motif — pieces arranged in a ring or rectangle

**Trigger:** `shape` keyword present.

```
object tree  label forest  count 12 shape circle    radius 7 clusters 4 spread 1
object fence label yard    count 20 shape rectangle radius 6
object post  label corners count 4  shape square    radius 4 arc 0.25
```

| Keyword | Type | Meaning |
|---|---|---|
| `shape circle` | — | Ring of pieces around anchor |
| `shape rectangle` | — | Rectangular perimeter around anchor |
| `shape square` | — | Square perimeter (equal width/depth) |
| `radius N` | int | Ring radius or half-width of rectangle |
| `clusters N` | int | Divide ring into N clusters. Defaults to `count`. Set lower for grouped clumps |
| `spread F` | float | How far each piece can drift from its ideal slot (0 = exact, 1 = ±1 cell) |
| `arc F` | float | 0.0–1.0, fraction of the full ring to fill. `arc 0.5` = semicircle |

### 2. Path — turtle walks from the anchor in a direction

**Trigger:** `from` and `heading` present, no `shape`.

```
object road  label path    steps 12 from campfire heading south wobble 0.2
object road  label trail   steps 15 from campfire heading east  wobble 0.1 to market_0
object fence label wall    count 8  from campfire heading north wobble 0.0
```

| Keyword | Type | Meaning |
|---|---|---|
| `from <label>` | string | Starting reference (label of anchor or piece). Currently defines intent; path always starts just outside the MA zone |
| `heading <dir>` | string | `north`, `south`, `east`, `west` |
| `steps N` | int | Number of path cells. Alias for `count` in path mode — use whichever reads more naturally |
| `wobble F` | float | Jitter (0 = perfectly straight, 0.3 = natural-feeling curves) |
| `to <label>` | string | **Terminus.** Path steers toward this piece and stops when adjacent. Unused steps are skipped |

`to` resolves by piece **type or label** — whichever matches first.

### 3. Follow — pieces attach alongside another group

**Trigger:** `target` present, no `shape`.

```
object lantern label lights  count 6 target road    side any   distance 1 spacing 2
object bench   label seating count 4 target fountain side east distance 2 spacing 1
object log     label firewood count 3 target campfire side any  distance 1 spacing 1
```

| Keyword | Type | Meaning |
|---|---|---|
| `target <label>` | string | Group to follow. Matches by `piece.type`, `piece.group`, or `piece.label` — whichever matches first |
| `side <s>` | string | `any`, `left`, `right`, `north`, `south`, `east`, `west` |
| `distance N` | int | Offset from the target piece in grid cells |
| `spacing N` | int | Only attach to every Nth target piece (controls density) |

### 4. Scatter — pieces distributed within a radius

**Trigger:** `radius` or `near` present, no `shape`/`from`/`target`.

```
object rubble  label clutter  count 4 radius 10
object barrel  label supplies count 3 near campfire radius 3
object bush    label undergrowth count 5 near forest_0 radius 2
```

| Keyword | Type | Meaning |
|---|---|---|
| `radius N` | int | Scatter within N grid cells of the center |
| `near <label>` | string | **Anchor.** Scatter within `radius` cells of this piece instead of the scene center. Resolves by type or label |

`near` without `radius` defaults to `radius 8`.

---

## Dispatch priority

When a line has multiple keywords, the solver picks the mode by this order:

| Priority | Condition | Mode |
|---|---|---|
| 1 | `shape` present | Motif |
| 2 | `from` + `heading` present | Path |
| 3 | `target` present | Follow |
| 4 | `radius` or `near` present | Scatter |

**Any type can use any mode.** Trees can follow a path. Lanterns can form rings.
Fences can scatter. The `type` name is just a label for context packets; it doesn't
constrain how pieces are placed.

---

## Symbol override

```
object bonfire label center count 1 shape circle radius 0 symbol @
```

`symbol <char>` overrides the single character used in the ASCII top-down view for
this object type. Useful when the default first-letter conflicts with another type.

---

## Full keyword list

| Keyword | Type | Used in |
|---|---|---|
| `label` | string | All |
| `count` | int | All |
| `shape` | string | Motif |
| `radius` | int | Motif (ring size), Scatter (zone) |
| `clusters` | int | Motif |
| `spread` | float | Motif |
| `arc` | float | Motif |
| `from` | string | Path |
| `heading` | string | Path |
| `steps` | int | Path (alias for count) |
| `wobble` | float | Path |
| `to` | string | Path terminus |
| `target` | string | Follow |
| `side` | string | Follow |
| `distance` | int | Follow |
| `spacing` | int | Follow |
| `near` | string | Scatter anchor |
| `symbol` | string | All (ASCII override) |

---

## Examples

### Campsite

```
anchor campfire fire_pit
ma hard radius 4

object tree    label forest    count 10 shape circle radius 7 clusters 3 spread 1
object log     label firewood  count 3  near fire_pit radius 2
object road    label main_path steps 14 from fire_pit heading south wobble 0.2
object lantern label lights    count 4  target road side any distance 1 spacing 3
object rubble  label clutter   count 3  radius 10
```

### Market with approach road

```
anchor fountain market_center
ma hard radius 3

object stall   label stalls    count 8  shape circle radius 6 clusters 4 spread 1
object road    label approach  steps 12 from market_center heading south wobble 0.1
object lantern label gate_lights count 2 target road side any distance 1 spacing 5
object crate   label goods     count 4  near stall_0 radius 2
```

### Forest shrine with terminus path

```
anchor altar shrine
ma hard radius 3

object tree   label grove   count 14 shape circle radius 8 clusters 5 spread 1
object statue label guardians count 2 shape circle radius 5 arc 0.3
object road   label approach steps 18 from shrine heading south wobble 0.15 to grove_0
object lantern label path_lights count 5 target road side any distance 1 spacing 3
```

The path walks south from the shrine, steers toward `grove_0`, and stops when
adjacent — so it terminates at the treeline rather than in open space.

---

## Tips

- **Anchor first.** It's the spatial root. Every radius is measured from it unless
  `near` overrides.
- **Use `ma` to keep the anchor visible.** Without it, pieces can land directly on the
  focal point.
- **`steps` reads more naturally than `count` for paths.** Both work.
- **`to` fixes dead-end paths.** Without it, a path just walks N steps and stops wherever.
  With it, the path terminates at a real destination.
- **`near` fixes orphaned props.** `object barrel radius 8` scatters relative to center
  (often landing in empty space). `object barrel near campfire radius 3` clusters barrels
  where they make narrative sense.
- **Order matters for `target` and `to`.** The piece must be declared in an earlier line.
  `object lantern target road` only works if the `road` line came first.
- **Small counts first.** A ring of 4 trees is faster to verify than a ring of 12.
  Once the layout reads right, bump the count.
- **Iterate DSL, not geometry.** If a piece lands wrong, change the DSL and re-solve.
  The solver runs in ~2ms. Don't try to fix placement by tweaking primitive positions.

---

## When things go wrong

**"Nothing placed for this object"** — the solver couldn't find a valid cell. Usually:
counts too high for the available space, `ma` zone too large, or `radius` too small.

**"Path only placed N of M steps"** — no valid cell in the heading direction (hit edge or
occupied cells). Reduce wobble, change heading, or reduce step count.

**"Lanterns not placing"** — `target road` matches `piece.type == 'road'`. If your road
line uses a different `type` word (e.g. `object trail`), use `target trail`.

**"Barrel near tent not near tent"** — `near tent` matches `piece.type == 'tent'` or
`piece.label == 'tent'`. If the tent pieces have label `camping_0`, use `near camping`
(matches by type) or the exact label.

**"to isn't stopping the path"** — the target piece must be placed before the road line.
Reorder the object declarations.

---

## What the parser does NOT support

- Multi-line `object` blocks (indented syntax) — that's the topology_candidate system,
  not the main solver.
- `inside`, `outside`, `around`, `along`, `roles`, `traits`, `importance`, `socket` —
  topology_candidate keywords, ignored by the main parser.
- Diagonal headings (`northeast`, `se`, etc.) — only `north`, `south`, `east`, `west`.
- Multiple anchors — exactly one `anchor` line per scene.

---

## See also

- `scripts/dropgrid/parser.py` — authoritative source; if in doubt, read the code
- `scripts/dropgrid/solver.py` — what each mode actually does at placement time
- `references/worked_examples/full_loop_example.md` — complete DSL → HTML trace
- `SKILL.md §2` — how to write DSL as part of the full pipeline workflow

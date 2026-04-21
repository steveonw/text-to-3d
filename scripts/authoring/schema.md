# Geometry Packet Schema

A geometry packet describes the visual appearance of one placed piece as a list
of Three.js-style primitives in the piece's **local coordinate space**.

## Coordinate conventions

- **y-up** — positive y is "up"
- **y = 0** is the floor (ground level)
- **x / z** are the horizontal axes
- All positions and dimensions are in **scene units** (one grid cell ≈ 1 unit)
- Rotation values are in **degrees**, applied as Euler angles (x, y, z order)

---

## Packet

```json
{
  "piece_id": 3,
  "primitives": [ ...primitive objects... ]
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `piece_id` | non-negative integer | yes | matches `Piece.id` from the solver |
| `primitives` | non-empty array | yes | one or more primitive objects |

---

## Primitive

```json
{
  "shape": "box",
  "dimensions": [1.0, 2.0, 1.0],
  "position": [0.0, 1.0, 0.0],
  "rotation": [0.0, 0.0, 0.0],
  "material": { "color": "#8b6914" }
}
```

### `shape`

One of: `box`, `cylinder`, `cone`, `sphere`, `plane`

### `dimensions`

Shape-specific list of **positive** numbers:

| Shape | Count | Values |
|-------|-------|--------|
| `box` | 3 | `[width, height, depth]` |
| `cylinder` | 3 | `[radius_top, radius_bottom, height]` |
| `cone` | 2 | `[radius, height]` |
| `sphere` | 1 | `[radius]` |
| `plane` | 2 | `[width, height]` |

### `position`

`[x, y, z]` — offset from the piece's grid anchor in scene units.
Defaults to `[0.0, 0.0, 0.0]` if omitted.

### `rotation`

`[rx, ry, rz]` — Euler rotation in degrees.
Defaults to `[0.0, 0.0, 0.0]` if omitted.

---

## Material

```json
{
  "color": "#a07850",
  "roughness": 0.8,
  "metalness": 0.05,
  "emissive": "#ff6600",
  "emissive_intensity": 0.4
}
```

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `color` | string | yes | — | 6-digit hex, e.g. `"#a1b2c3"` |
| `roughness` | float [0, 1] | no | `0.85` | 0 = mirror, 1 = fully rough |
| `metalness` | float [0, 1] | no | `0.05` | 0 = dielectric, 1 = metal |
| `emissive` | string | no | — | hex color; omit for non-glowing materials |
| `emissive_intensity` | float ≥ 0 | no | `0.5` | only used when `emissive` is set |

---

## Example — a simple tree

```json
{
  "piece_id": 7,
  "primitives": [
    {
      "shape": "cylinder",
      "dimensions": [0.15, 0.15, 0.9],
      "position": [0.0, 0.45, 0.0],
      "rotation": [0.0, 0.0, 0.0],
      "material": { "color": "#5c3d1e", "roughness": 0.9 }
    },
    {
      "shape": "cone",
      "dimensions": [0.55, 1.4],
      "position": [0.0, 1.6, 0.0],
      "rotation": [0.0, 0.0, 0.0],
      "material": { "color": "#2d5a27", "roughness": 0.85 }
    }
  ]
}
```

## Example — a glowing lantern

```json
{
  "piece_id": 12,
  "primitives": [
    {
      "shape": "box",
      "dimensions": [0.3, 0.05, 0.3],
      "position": [0.0, 1.2, 0.0],
      "material": { "color": "#444444", "roughness": 0.6, "metalness": 0.4 }
    },
    {
      "shape": "box",
      "dimensions": [0.22, 0.35, 0.22],
      "position": [0.0, 1.375, 0.0],
      "material": {
        "color": "#ffdd88",
        "roughness": 0.3,
        "emissive": "#ffcc44",
        "emissive_intensity": 0.8
      }
    }
  ]
}
```

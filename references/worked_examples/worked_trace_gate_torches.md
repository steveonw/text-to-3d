# Worked Compilation Trace Fixture — Gate + Torches

## DSL
```text
object fence
  label yard_edge
  roles barrier boundary
  mode rect_perimeter
  importance primary

object gate
  label front_gate
  roles gate_opening gate_frame
  target yard_edge
  socket opening
  facing south
  importance primary

object fountain
  label shrine_center
  inside yard_edge
  importance primary

object torch
  label gate_torches
  count 2
  roles marker
  target yard_edge
  socket face
  near front_gate
```

## Parse summary
- object count: 4
- labels: yard_edge, front_gate, shrine_center, gate_torches

## Normalized objects
```json
[
  {
    "kind": "fence",
    "label": "yard_edge",
    "count": 1,
    "roles": [
      "barrier",
      "boundary"
    ],
    "mode": "rect_perimeter",
    "target": null,
    "inside": null,
    "outside": null,
    "around": null,
    "along": null,
    "near": null,
    "facing": null,
    "socket": null,
    "align": null,
    "traits": [],
    "importance": "primary",
    "host_ref": null,
    "align_ref": null,
    "target_kind": null,
    "zone_kind": null,
    "inferred_roles": [],
    "warnings": []
  },
  {
    "kind": "gate",
    "label": "front_gate",
    "count": 1,
    "roles": [
      "gate_opening",
      "gate_frame"
    ],
    "mode": "attach",
    "target": "yard_edge",
    "inside": null,
    "outside": null,
    "around": null,
    "along": null,
    "near": null,
    "facing": "south",
    "socket": "opening",
    "align": null,
    "traits": [],
    "importance": "primary",
    "host_ref": "yard_edge",
    "align_ref": null,
    "target_kind": "fence",
    "zone_kind": null,
    "inferred_roles": [],
    "warnings": []
  },
  {
    "kind": "fountain",
    "label": "shrine_center",
    "count": 1,
    "roles": [],
    "mode": "center",
    "target": null,
    "inside": "yard_edge",
    "outside": null,
    "around": null,
    "along": null,
    "near": null,
    "facing": null,
    "socket": null,
    "align": null,
    "traits": [],
    "importance": "primary",
    "host_ref": "yard_edge",
    "align_ref": null,
    "target_kind": null,
    "zone_kind": "fence",
    "inferred_roles": [],
    "warnings": []
  },
  {
    "kind": "torch",
    "label": "gate_torches",
    "count": 2,
    "roles": [
      "marker"
    ],
    "mode": "attach",
    "target": "yard_edge",
    "inside": null,
    "outside": null,
    "around": null,
    "along": null,
    "near": "front_gate",
    "facing": null,
    "socket": "face",
    "align": null,
    "traits": [],
    "importance": "secondary",
    "host_ref": "yard_edge",
    "align_ref": null,
    "target_kind": "fence",
    "zone_kind": null,
    "inferred_roles": [],
    "warnings": []
  }
]
```

## Emitter intents
```json
[
  {
    "kind": "fence",
    "label": "yard_edge",
    "count": 1,
    "emit": {
      "shape": "rectangle",
      "placement_mode": "motif",
      "radius": 4,
      "distance": 4,
      "count": 28,
      "step": 1
    },
    "relations": {},
    "traits": [],
    "importance": "primary"
  },
  {
    "kind": "gate",
    "label": "front_gate",
    "count": 1,
    "emit": {
      "shape": "fixed_slots",
      "placement_mode": "attach",
      "count": 1,
      "socket": "opening"
    },
    "relations": {
      "target": "yard_edge",
      "facing": "south",
      "socket": "opening",
      "special_op": {
        "type": "gate_opening",
        "side": "south",
        "span": 2
      }
    },
    "traits": [],
    "importance": "primary"
  },
  {
    "kind": "fountain",
    "label": "shrine_center",
    "count": 1,
    "emit": {
      "shape": "fixed_center",
      "placement_mode": "fixed",
      "count": 1,
      "max_nudge": 3
    },
    "relations": {
      "inside": "yard_edge"
    },
    "traits": [],
    "importance": "primary"
  },
  {
    "kind": "torch",
    "label": "gate_torches",
    "count": 2,
    "emit": {
      "shape": "fixed_slots",
      "placement_mode": "attach",
      "count": 2,
      "socket": "face"
    },
    "relations": {
      "target": "yard_edge",
      "near": "front_gate",
      "socket": "face"
    },
    "traits": [],
    "importance": "secondary"
  }
]
```

## Legacy solver spec
```json
{
  "anchor": {
    "type": "fountain",
    "label": "shrine_center"
  },
  "ma": null,
  "objects": [
    {
      "type": "fence",
      "label": "yard_edge",
      "count": 28,
      "placement_mode": "motif",
      "shape": "rectangle",
      "radius": 4,
      "distance": 4,
      "target": "shrine_center"
    },
    {
      "type": "torch",
      "label": "gate_torches",
      "count": 2,
      "placement_mode": "follow",
      "target": "yard_edge",
      "distance": 1,
      "spacing": 1
    }
  ],
  "warnings": [],
  "layout_special_ops": [
    {
      "type": "gate_opening",
      "gate_label": "front_gate",
      "target_group": "yard_edge",
      "side": "south",
      "span": 2,
      "kind": "gate"
    }
  ]
}
```

## Runtime trace
```json
{
  "hosts": {},
  "gate_ops": [],
  "attach_ops": []
}
```

## Piece summaries
```json
[
  {
    "id": 1,
    "type": "fountain",
    "label": "shrine_center",
    "group": "shrine_center",
    "gx": 14,
    "gz": 12,
    "rot": 0,
    "meta": {}
  },
  {
    "id": 2,
    "type": "fence",
    "label": "yard_edge_0",
    "group": "yard_edge",
    "gx": 10,
    "gz": 8,
    "rot": 0,
    "meta": {
      "variant": "E",
      "connection_count": 1
    }
  },
  {
    "id": 3,
    "type": "fence",
    "label": "yard_edge_1",
    "group": "yard_edge",
    "gx": 12,
    "gz": 8,
    "rot": 0,
    "meta": {
      "variant": "ESW",
      "connection_count": 3
    }
  },
  {
    "id": 4,
    "type": "fence",
    "label": "yard_edge_2",
    "group": "yard_edge",
    "gx": 12,
    "gz": 9,
    "rot": 0,
    "meta": {
      "variant": "NE",
      "connection_count": 2
    }
  },
  {
    "id": 5,
    "type": "fence",
    "label": "yard_edge_3",
    "group": "yard_edge",
    "gx": 14,
    "gz": 8,
    "rot": 0,
    "meta": {
      "variant": "ESW",
      "connection_count": 3
    }
  },
  {
    "id": 6,
    "type": "fence",
    "label": "yard_edge_4",
    "group": "yard_edge",
    "gx": 14,
    "gz": 9,
    "rot": 0,
    "meta": {
      "variant": "NEW",
      "connection_count": 3
    }
  },
  {
    "id": 7,
    "type": "fence",
    "label": "yard_edge_5",
    "group": "yard_edge",
    "gx": 16,
    "gz": 8,
    "rot": 0,
    "meta": {
      "variant": "ESW",
      "connection_count": 3
    }
  },
  {
    "id": 8,
    "type": "fence",
    "label": "yard_edge_6",
    "group": "yard_edge",
    "gx": 16,
    "gz": 9,
    "rot": 0,
    "meta": {
      "variant": "NEW",
      "connection_count": 3
    }
  },
  {
    "id": 9,
    "type": "fence",
    "label": "yard_edge_7",
    "group": "yard_edge",
    "gx": 18,
    "gz": 8,
    "rot": 0,
    "meta": {
      "variant": "SW",
      "connection_count": 2
    }
  },
  {
    "id": 10,
    "type": "fence",
    "label": "yard_edge_8",
    "group": "yard_edge",
    "gx": 18,
    "gz": 9,
    "rot": 1,
    "meta": {
      "variant": "NESW",
      "connection_count": 4
    }
  },
  {
    "id": 11,
    "type": "fence",
    "label": "yard_edge_9",
    "group": "yard_edge",
    "gx": 19,
    "gz": 10,
    "rot": 1,
    "meta": {
      "variant": "SW",
      "connection_count": 3
    }
  },
  {
    "id": 12,
    "type": "fence",
    "label": "yard_edge_10",
    "group": "yard_edge",
    "gx": 18,
    "gz": 11,
    "rot": 1,
    "meta": {
      "variant": "NES",
      "connection_count": 4
    }
  },
  {
    "id": 13,
    "type": "fence",
    "label": "yard_edge_11",
    "group": "yard_edge",
    "gx": 19,
    "gz": 12,
    "rot": 1,
    "meta": {
      "variant": "NSW",
      "connection_count": 4
    }
  },
  {
    "id": 14,
    "type": "fence",
    "label": "yard_edge_12",
    "group": "yard_edge",
    "gx": 18,
    "gz": 13,
    "rot": 1,
    "meta": {
      "variant": "NE",
      "connection_count": 3
    }
  },
  {
    "id": 15,
    "type": "fence",
    "label": "yard_edge_13",
    "group": "yard_edge",
    "gx": 19,
    "gz": 14,
    "rot": 1,
    "meta": {
      "variant": "NW",
      "connection_count": 2
    }
  },
  {
    "id": 16,
    "type": "fence",
    "label": "yard_edge_14",
    "group": "yard_edge",
    "gx": 18,
    "gz": 16,
    "rot": 1,
    "meta": {
      "variant": "W",
      "connection_count": 2
    }
  },
  {
    "id": 17,
    "type": "fence",
    "label": "yard_edge_15",
    "group": "yard_edge",
    "gx": 16,
    "gz": 16,
    "rot": 0,
    "meta": {
      "variant": "ESW",
      "connection_count": 3
    }
  },
  {
    "id": 18,
    "type": "fence",
    "label": "yard_edge_16",
    "group": "yard_edge",
    "gx": 16,
    "gz": 17,
    "rot": 0,
    "meta": {
      "variant": "NEW",
      "connection_count": 3
    }
  },
  {
    "id": 19,
    "type": "fence",
    "label": "yard_edge_17",
    "group": "yard_edge",
    "gx": 14,
    "gz": 16,
    "rot": 0,
    "meta": {
      "variant": "ESW",
      "connection_count": 3
    }
  },
  {
    "id": 20,
    "type": "fence",
    "label": "yard_edge_18",
    "group": "yard_edge",
    "gx": 14,
    "gz": 17,
    "rot": 0,
    "meta": {
      "variant": "NEW",
      "connection_count": 3
    }
  },
  {
    "id": 21,
    "type": "fence",
    "label": "yard_edge_19",
    "group": "yard_edge",
    "gx": 12,
    "gz": 16,
    "rot": 0,
    "meta": {
      "variant": "ESW",
      "connection_count": 3
    }
  },
  {
    "id": 22,
    "type": "fence",
    "label": "yard_edge_20",
    "group": "yard_edge",
    "gx": 12,
    "gz": 17,
    "rot": 0,
    "meta": {
      "variant": "NE",
      "connection_count": 2
    }
  },
  {
    "id": 23,
    "type": "fence",
    "label": "yard_edge_21",
    "group": "yard_edge",
    "gx": 10,
    "gz": 16,
    "rot": 0,
    "meta": {
      "variant": "NEW",
      "connection_count": 3
    }
  },
  {
    "id": 24,
    "type": "fence",
    "label": "yard_edge_22",
    "group": "yard_edge",
    "gx": 9,
    "gz": 15,
    "rot": 1,
    "meta": {
      "variant": "E",
      "connection_count": 2
    }
  },
  {
    "id": 25,
    "type": "fence",
    "label": "yard_edge_23",
    "group": "yard_edge",
    "gx": 10,
    "gz": 14,
    "rot": 1,
    "meta": {
      "variant": "NESW",
      "connection_count": 4
    }
  },
  {
    "id": 26,
    "type": "fence",
    "label": "yard_edge_24",
    "group": "yard_edge",
    "gx": 11,
    "gz": 13,
    "rot": 1,
    "meta": {
      "variant": "NW",
      "connection_count": 3
    }
  },
  {
    "id": 27,
    "type": "fence",
    "label": "yard_edge_25",
    "group": "yard_edge",
    "gx": 10,
    "gz": 12,
    "rot": 1,
    "meta": {
      "variant": "NES",
      "connection_count": 4
    }
  },
  {
    "id": 28,
    "type": "fence",
    "label": "yard_edge_26",
    "group": "yard_edge",
    "gx": 11,
    "gz": 11,
    "rot": 1,
    "meta": {
      "variant": "SW",
      "connection_count": 3
    }
  },
  {
    "id": 29,
    "type": "fence",
    "label": "yard_edge_27",
    "group": "yard_edge",
    "gx": 10,
    "gz": 10,
    "rot": 1,
    "meta": {
      "variant": "ES",
      "connection_count": 2
    }
  },
  {
    "id": 30,
    "type": "torch",
    "label": "gate_torches_0",
    "group": "gate_torches",
    "gx": 10,
    "gz": 7,
    "rot": 2,
    "meta": {
      "host_label": "yard_edge_0",
      "socket_class": "wall_face"
    }
  },
  {
    "id": 31,
    "type": "torch",
    "label": "gate_torches_1",
    "group": "gate_torches",
    "gx": 11,
    "gz": 7,
    "rot": 2,
    "meta": {
      "host_label": "yard_edge_0",
      "socket_class": "wall_face"
    }
  }
]
```

## ASCII
```text
······················
······················
······················
······················
······················
······················
······················
··········TT··········
··········HHHHHHHHHH··
············HHHHHHH···
··········H·······HH··
··········HH······HH··
··········HH··FF··HH··
··········HH··FF··HH··
·········=HH······HH··
·········HH········H··
·········HHHHHHHHHH···
············HHHHHHH···
······················
······················
```

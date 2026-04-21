#!/usr/bin/env python3
"""layout_compare.py — summarize or compare grouped spatial layouts.

Input JSON format:
{
  "room": {"width": 14, "depth": 10},
  "items": [
    {"name": "tableA", "x": -2.7, "z": -2.1, "w": 1.0, "d": 1.0, "group": "table"}
  ],
  "zones": [
    {"name": "piano_keepout", "xmin": 3.0, "xmax": 5.5, "zmin": 3.2, "zmax": 5.0}
  ]
}
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def filter_items(data: dict[str, Any], group: str | None, prefix: str | None):
    items = data.get("items", [])
    if group:
        items = [it for it in items if it.get("group") == group]
    if prefix:
        items = [it for it in items if it.get("name", "").startswith(prefix)]
    return items


def dist(a, b):
    return math.hypot(a["x"] - b["x"], a["z"] - b["z"])


def rect_edges(item):
    w = item.get("w", 0.0)
    d = item.get("d", 0.0)
    return item["x"] - w / 2, item["x"] + w / 2, item["z"] - d / 2, item["z"] + d / 2


def overlaps_zone(item, zone):
    ix0, ix1, iz0, iz1 = rect_edges(item)
    return not (ix1 <= zone["xmin"] or ix0 >= zone["xmax"] or iz1 <= zone["zmin"] or iz0 >= zone["zmax"])


def summarize(data: dict[str, Any], items: list[dict[str, Any]]):
    if not items:
        return {"count": 0}
    xs = [it["x"] for it in items]
    zs = [it["z"] for it in items]
    centroid = {"x": sum(xs) / len(xs), "z": sum(zs) / len(zs)}
    pairs = []
    nearest = None
    for i, a in enumerate(items):
        best = None
        for j, b in enumerate(items):
            if i == j:
                continue
            d = dist(a, b)
            if best is None or d < best:
                best = d
            pairs.append((a["name"], b["name"], d))
        a["_nn"] = best
    avg_nn = sum(it["_nn"] for it in items if it.get("_nn") is not None) / len(items)
    min_pair = min((p for p in pairs if p[0] < p[1]), key=lambda x: x[2], default=None)
    room = data.get("room", {})
    half_x = 0.0
    half_z = 0.0
    left = sum(1 for it in items if it["x"] < half_x)
    right = len(items) - left
    front = sum(1 for it in items if it["z"] < half_z)
    back = len(items) - front
    quadrants = {
        "front_left": sum(1 for it in items if it["x"] < 0 and it["z"] < 0),
        "front_right": sum(1 for it in items if it["x"] >= 0 and it["z"] < 0),
        "back_left": sum(1 for it in items if it["x"] < 0 and it["z"] >= 0),
        "back_right": sum(1 for it in items if it["x"] >= 0 and it["z"] >= 0),
    }
    collisions = []
    for zone in data.get("zones", []):
        hits = [it["name"] for it in items if overlaps_zone(it, zone)]
        if hits:
            collisions.append({"zone": zone["name"], "items": hits})
    return {
        "count": len(items),
        "room": room,
        "centroid": centroid,
        "x_span": [min(xs), max(xs)],
        "z_span": [min(zs), max(zs)],
        "left_right": {"left": left, "right": right},
        "front_back": {"front": front, "back": back},
        "quadrants": quadrants,
        "avg_nearest_neighbor": round(avg_nn, 3),
        "closest_pair": None if min_pair is None else {"a": min_pair[0], "b": min_pair[1], "distance": round(min_pair[2], 3)},
        "zone_collisions": collisions,
    }


def print_summary(summary):
    print(json.dumps(summary, indent=2))
    if summary.get("count", 0) == 0:
        return
    lr = summary["left_right"]
    fb = summary["front_back"]
    quads = summary["quadrants"]
    print("\nRead:")
    print(f"- items: {summary['count']}")
    print(f"- centroid: ({summary['centroid']['x']:.2f}, {summary['centroid']['z']:.2f})")
    print(f"- left/right: {lr['left']} / {lr['right']}")
    print(f"- front/back: {fb['front']} / {fb['back']}")
    print(f"- average nearest neighbor: {summary['avg_nearest_neighbor']:.2f}")
    cp = summary.get("closest_pair")
    if cp:
        print(f"- closest pair: {cp['a']} ↔ {cp['b']} = {cp['distance']:.2f}m")
    print(f"- quadrants: {quads}")
    if summary.get("zone_collisions"):
        print(f"- zone collisions: {summary['zone_collisions']}")


def compare(before, after, items_before, items_after):
    s1 = summarize(before, items_before)
    s2 = summarize(after, items_after)
    moved = []
    before_map = {it['name']: it for it in items_before}
    after_map = {it['name']: it for it in items_after}
    for name, b in before_map.items():
        a = after_map.get(name)
        if not a:
            continue
        dx = round(a['x'] - b['x'], 3)
        dz = round(a['z'] - b['z'], 3)
        if dx or dz:
            moved.append({"name": name, "dx": dx, "dz": dz})
    result = {
        "before": s1,
        "after": s2,
        "delta": {
            "centroid_x": round(s2.get('centroid', {}).get('x', 0) - s1.get('centroid', {}).get('x', 0), 3),
            "centroid_z": round(s2.get('centroid', {}).get('z', 0) - s1.get('centroid', {}).get('z', 0), 3),
            "avg_nearest_neighbor": round(s2.get('avg_nearest_neighbor', 0) - s1.get('avg_nearest_neighbor', 0), 3),
        },
        "moved_items": moved,
    }
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Summarize or compare grouped layouts")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("summary")
    p1.add_argument("layout")
    p1.add_argument("--group")
    p1.add_argument("--prefix")
    p2 = sub.add_parser("compare")
    p2.add_argument("before")
    p2.add_argument("after")
    p2.add_argument("--group")
    p2.add_argument("--prefix")
    args = parser.parse_args()

    if args.cmd == "summary":
        data = load(args.layout)
        items = filter_items(data, args.group, args.prefix)
        print_summary(summarize(data, items))
    else:
        before = load(args.before)
        after = load(args.after)
        ib = filter_items(before, args.group, args.prefix)
        ia = filter_items(after, args.group, args.prefix)
        compare(before, after, ib, ia)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
path_walk.py — Narrated spatial walk through a scene.

Walks a line through the scene and reports what's nearby at each step.
Catches: path discontinuities, dead gaps, chokepoints, awkward entrances,
props intruding into movement lanes, facade transitions.

Usage:
    # Walk central axis south to north
    python scripts/path_walk.py scene.json --axis-x 18 --from-z 0 --to-z 40

    # Walk a custom path (list of x,z waypoints)
    python scripts/path_walk.py scene.json --waypoints "18,0 18,9 20,15 18,20"

    # Adjust scan radius and step size
    python scripts/path_walk.py scene.json --axis-x 18 --from-z 0 --to-z 30 --step 1 --radius 4

    # Output as JSON for machine consumption
    python scripts/path_walk.py scene.json --axis-x 18 --from-z 0 --to-z 40 --json
"""

import argparse
import json
import math
import sys


def load_scene(path):
    with open(path) as f:
        return json.load(f)


def direction_label(dx, dz, heading_z_positive=True):
    """Relative direction from walker's perspective (walking toward +z by default)."""
    angle = math.atan2(dx, dz)  # angle from +z axis
    deg = math.degrees(angle)
    if -30 < deg < 30:
        return "ahead"
    elif 30 <= deg < 80:
        return "ahead-right"
    elif 80 <= deg < 100:
        return "right"
    elif 100 <= deg < 150:
        return "behind-right"
    elif deg >= 150 or deg <= -150:
        return "behind"
    elif -150 < deg <= -100:
        return "behind-left"
    elif -100 < deg <= -80:
        return "left"
    elif -80 < deg <= -30:
        return "ahead-left"
    return "nearby"


def scan_nearby(objects, px, pz, radius=5.0, max_results=8):
    """Find objects near a position. Returns sorted by distance."""
    hits = []
    for o in objects:
        ox, oz = o['x'], o['z']
        ow, od = o.get('w', 1), o.get('d', 1)
        
        # Distance to object center
        dist = math.sqrt((px - ox)**2 + (pz - oz)**2)
        
        # Distance to nearest edge (approximate)
        edge_dx = max(0, abs(px - ox) - ow/2)
        edge_dz = max(0, abs(pz - oz) - od/2)
        edge_dist = math.sqrt(edge_dx**2 + edge_dz**2)
        
        if edge_dist < radius:
            dx = ox - px
            dz = oz - pz
            facing = direction_label(dx, dz)
            h = o.get('h', 1)
            hits.append({
                'name': o['name'],
                'template': o.get('template', '?'),
                'dist': round(dist, 1),
                'edge_dist': round(edge_dist, 1),
                'direction': facing,
                'height': h,
                'dx': round(dx, 1),
                'dz': round(dz, 1),
            })
    
    hits.sort(key=lambda h: h['dist'])
    return hits[:max_results]


def detect_gaps(steps):
    """Find dead gaps — stretches where nothing is ahead within 3m."""
    gaps = []
    current_gap_start = None
    
    for step in steps:
        ahead_objects = [h for h in step['nearby'] if 'ahead' in h['direction'] and h['dist'] < 4]
        if not ahead_objects and not any(h['dist'] < 1.5 for h in step['nearby']):
            if current_gap_start is None:
                current_gap_start = step['z']
        else:
            if current_gap_start is not None:
                gap_len = step['z'] - current_gap_start
                if gap_len >= 2:
                    gaps.append({
                        'from_z': current_gap_start,
                        'to_z': step['z'],
                        'length': round(gap_len, 1),
                        'note': f"Dead gap: {gap_len:.1f}m of empty ground"
                    })
                current_gap_start = None
    
    return gaps


def detect_chokepoints(steps, objects, walk_x, min_clearance=1.5):
    """Find places where objects on both sides create narrow passages."""
    chokes = []
    for step in steps:
        left = [h for h in step['nearby'] if 'left' in h['direction'] and h['edge_dist'] < min_clearance]
        right = [h for h in step['nearby'] if 'right' in h['direction'] and h['edge_dist'] < min_clearance]
        if left and right:
            chokes.append({
                'z': step['z'],
                'left': left[0]['name'],
                'right': right[0]['name'],
                'left_dist': left[0]['edge_dist'],
                'right_dist': right[0]['edge_dist'],
                'clearance': round(left[0]['edge_dist'] + right[0]['edge_dist'], 1),
            })
    return chokes


def detect_facade_transitions(steps):
    """Detect when the dominant nearby object changes — marks zone transitions."""
    transitions = []
    prev_dominant = None
    
    for step in steps:
        ahead = [h for h in step['nearby'] if 'ahead' in h['direction']]
        dominant = ahead[0]['name'] if ahead else None
        
        if dominant and dominant != prev_dominant and prev_dominant is not None:
            transitions.append({
                'z': step['z'],
                'from': prev_dominant,
                'to': dominant,
            })
        if dominant:
            prev_dominant = dominant
    
    return transitions


def walk_axis(scene, axis_x, from_z, to_z, step=2.0, radius=5.0):
    """Walk along an axis line, scanning at each step."""
    objects = scene['objects']
    steps = []
    
    z = from_z
    while z <= to_z:
        nearby = scan_nearby(objects, axis_x, z, radius)
        steps.append({
            'x': axis_x,
            'z': z,
            'nearby': nearby,
        })
        z += step
    
    return steps


def walk_waypoints(scene, waypoints, step=1.0, radius=5.0):
    """Walk along a series of waypoints, interpolating between them."""
    objects = scene['objects']
    steps = []
    
    for i in range(len(waypoints) - 1):
        x1, z1 = waypoints[i]
        x2, z2 = waypoints[i + 1]
        dist = math.sqrt((x2-x1)**2 + (z2-z1)**2)
        n_steps = max(1, int(dist / step))
        
        for j in range(n_steps):
            t = j / n_steps
            px = x1 + t * (x2 - x1)
            pz = z1 + t * (z2 - z1)
            nearby = scan_nearby(objects, px, pz, radius)
            steps.append({
                'x': round(px, 1),
                'z': round(pz, 1),
                'nearby': nearby,
                'segment': i,
            })
    
    # Add final waypoint
    px, pz = waypoints[-1]
    nearby = scan_nearby(objects, px, pz, radius)
    steps.append({'x': px, 'z': pz, 'nearby': nearby, 'segment': len(waypoints)-2})
    
    return steps


def format_text(steps, gaps, chokes, transitions):
    """Human-readable walk report."""
    lines = []
    lines.append("═" * 55)
    lines.append("  PATH WALK REPORT")
    lines.append("═" * 55)
    lines.append("")
    
    for step in steps:
        z = step['z']
        x = step['x']
        nearby = step['nearby']
        
        if nearby:
            top = nearby[0]
            lines.append(f"  [{z:5.1f}m] nearest: {top['name']} ({top['direction']}, {top['dist']}m)")
            for h in nearby[1:4]:
                height_tag = f"↑{h['height']:.1f}m" if h['height'] > 1 else f"↓{h['height']:.1f}m"
                lines.append(f"           {h['direction']:12s} {h['dist']:4.1f}m — {h['name']} {height_tag}")
        else:
            lines.append(f"  [{z:5.1f}m] (empty — nothing within scan radius)")
        lines.append("")
    
    if gaps:
        lines.append("── DEAD GAPS ──")
        for g in gaps:
            lines.append(f"  ⚠ z={g['from_z']:.0f}→{g['to_z']:.0f}: {g['length']}m of empty ground")
        lines.append("")
    
    if chokes:
        lines.append("── CHOKEPOINTS ──")
        for c in chokes:
            lines.append(f"  ⚠ z={c['z']:.0f}: {c['left']} ← {c['clearance']}m → {c['right']}")
        lines.append("")
    
    if transitions:
        lines.append("── ZONE TRANSITIONS ──")
        for t in transitions:
            lines.append(f"  z={t['z']:.0f}: {t['from']} → {t['to']}")
        lines.append("")
    
    # Summary
    total_dist = steps[-1]['z'] - steps[0]['z'] if len(steps) > 1 else 0
    lines.append("── SUMMARY ──")
    lines.append(f"  Path length: {total_dist:.0f}m")
    lines.append(f"  Steps taken: {len(steps)}")
    lines.append(f"  Dead gaps:   {len(gaps)}")
    lines.append(f"  Chokepoints: {len(chokes)}")
    lines.append(f"  Transitions: {len(transitions)}")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Narrated path walk through a scene')
    parser.add_argument('scene', help='Path to scene.json')
    parser.add_argument('--axis-x', type=float, default=None, help='X coordinate for axis walk')
    parser.add_argument('--from-z', type=float, default=0, help='Start Z')
    parser.add_argument('--to-z', type=float, default=None, help='End Z')
    parser.add_argument('--waypoints', type=str, default=None, help='Custom waypoints "x1,z1 x2,z2 ..."')
    parser.add_argument('--step', type=float, default=2.0, help='Step size in meters')
    parser.add_argument('--radius', type=float, default=5.0, help='Scan radius')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parsed = parser.parse_args()
    
    scene = load_scene(parsed.scene)
    
    if parsed.waypoints:
        points = []
        for pair in parsed.waypoints.split():
            x, z = pair.split(',')
            points.append((float(x), float(z)))
        steps = walk_waypoints(scene, points, parsed.step, parsed.radius)
    elif parsed.axis_x is not None:
        to_z = parsed.to_z or scene['grid']['depth']
        steps = walk_axis(scene, parsed.axis_x, parsed.from_z, to_z, parsed.step, parsed.radius)
    else:
        # Auto-detect: walk the center of the grid
        cx = scene['grid']['width'] / 2
        steps = walk_axis(scene, cx, 0, scene['grid']['depth'], parsed.step, parsed.radius)
    
    gaps = detect_gaps(steps)
    chokes = detect_chokepoints(steps, scene['objects'], parsed.axis_x or scene['grid']['width']/2)
    transitions = detect_facade_transitions(steps)
    
    if parsed.json:
        result = {
            'steps': steps,
            'gaps': gaps,
            'chokepoints': chokes,
            'transitions': transitions,
        }
        print(json.dumps(result, indent=2))
    else:
        print(format_text(steps, gaps, chokes, transitions))


if __name__ == '__main__':
    main()

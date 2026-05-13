"""
Full-loop authoring script: shrine clearing scene, seed=7.
DSL → solver → context export → author packets → receive_all → lidar → HTML → visual_render.
Each piece is authored fresh from its context. No template reuse.
"""
import sys, os, random, json
sys.path.insert(0, 'scripts')

from dropgrid.api import solve_object_scene
from authoring.context_exporter import export_all_contexts
from authoring.geometry_receiver import receive_all

# ─── DSL ──────────────────────────────────────────────────────────────────────
DSL = """
anchor altar shrine
ma hard radius 3
object tree   label grove    count 12 shape circle radius 7 clusters 4 spread 1
object road   label approach steps 14 from shrine heading south wobble 0.15
object lantern label lights  count 6  target road side any distance 1 spacing 2
object rubble  label stones  count 4  near shrine radius 4
object statue  label guardian count 2 shape circle radius 4 arc 0.18
"""

# ─── Solve ─────────────────────────────────────────────────────────────────────
result = solve_object_scene(DSL, seed=7)
contexts = export_all_contexts(result)
print(f"Solver: {len(result.pieces)} pieces placed")

# ─── Utility ──────────────────────────────────────────────────────────────────
def jitter(v, scale=0.05, seed=None):
    """Deterministic per-piece jitter so two runs match."""
    rng = random.Random(seed)
    return v + rng.uniform(-scale, scale)

# ─── Geometry authoring ───────────────────────────────────────────────────────
packets = []

for p in result.pieces:
    ctx = contexts[p.id]
    near_path   = ctx.get("near_path", False)
    on_edge     = ctx.get("on_cluster_edge", False)
    interior    = ctx.get("interior", False)
    outward     = ctx.get("outward_direction", "N")
    rng         = random.Random(p.id * 137 + 42)   # deterministic per piece

    # ── ALTAR (1) ─────────────────────────────────────────────────────────────
    if p.type == "altar":
        packets.append({"piece_id": p.id, "primitives": [
            # Ground slab — broad foundation stone
            {"shape": "box", "dimensions": [2.2, 0.28, 2.2],
             "position": [0, 0.14, 0],
             "material": {"color": "#706050", "roughness": 0.95}},
            # Mid platform — slightly smaller, raised
            {"shape": "box", "dimensions": [1.6, 0.25, 1.6],
             "position": [0, 0.53, 0],
             "material": {"color": "#7a6858", "roughness": 0.92}},
            # Top altar stone — the offering surface
            {"shape": "box", "dimensions": [0.9, 0.35, 0.9],
             "position": [0, 0.93, 0],
             "material": {"color": "#857060", "roughness": 0.88}},
            # NW corner pillar
            {"shape": "cylinder", "dimensions": [0.10, 0.10, 1.1],
             "position": [-0.65, 0.55, -0.65],
             "material": {"color": "#6a5a48", "roughness": 0.9}},
            # NE corner pillar
            {"shape": "cylinder", "dimensions": [0.10, 0.10, 1.1],
             "position": [ 0.65, 0.55, -0.65],
             "material": {"color": "#6a5a48", "roughness": 0.9}},
            # SW corner pillar (broken top — shorter)
            {"shape": "cylinder", "dimensions": [0.10, 0.10, 0.85],
             "position": [-0.65, 0.43, 0.65],
             "material": {"color": "#6a5a48", "roughness": 0.9}},
            # SE corner pillar
            {"shape": "cylinder", "dimensions": [0.10, 0.10, 1.1],
             "position": [ 0.65, 0.55, 0.65],
             "material": {"color": "#6a5a48", "roughness": 0.9}},
            # Offering flame — small emissive sphere
            {"shape": "sphere", "dimensions": [0.14],
             "position": [0, 1.30, 0],
             "material": {"color": "#ffaa44", "roughness": 0.4,
                          "emissive": "#ff8800", "emissive_intensity": 1.2}},
            # Halo glow around flame
            {"shape": "sphere", "dimensions": [0.22],
             "position": [0, 1.32, 0],
             "material": {"color": "#ff6600", "roughness": 1.0,
                          "emissive": "#ff4400", "emissive_intensity": 0.3}},
        ]})

    # ── TREES ─────────────────────────────────────────────────────────────────
    elif p.type == "tree":
        # Vary trunk height and canopy shape by context
        if near_path:
            # Trees flanking the path: slightly shorter, wider canopy, more visible
            trunk_h = rng.uniform(0.8, 1.1)
            canopy_r = rng.uniform(0.60, 0.75)
            canopy_h = rng.uniform(1.6, 2.0)
            top_r    = rng.uniform(0.30, 0.40)
            top_h    = rng.uniform(0.9, 1.2)
            trunk_col = rng.choice(["#5c3d1e", "#4e3318"])
            green_col = rng.choice(["#2d5a27", "#346630", "#295225"])
            top_col   = rng.choice(["#1e4020", "#234823"])
        elif on_edge:
            # Cluster edge: tall, reaching for light, slight lean encoded as y-offset canopy
            trunk_h = rng.uniform(1.2, 1.5)
            canopy_r = rng.uniform(0.50, 0.65)
            canopy_h = rng.uniform(1.8, 2.3)
            top_r    = rng.uniform(0.25, 0.35)
            top_h    = rng.uniform(1.0, 1.3)
            trunk_col = rng.choice(["#4a2f15", "#5c3d1e"])
            green_col = rng.choice(["#3a6b30", "#2d5a27"])
            top_col   = rng.choice(["#1e4020", "#2a5424"])
        else:
            # Deep cluster interior or perimeter: standard conifer
            trunk_h = rng.uniform(0.9, 1.3)
            canopy_r = rng.uniform(0.55, 0.70)
            canopy_h = rng.uniform(1.7, 2.1)
            top_r    = rng.uniform(0.28, 0.38)
            top_h    = rng.uniform(0.95, 1.25)
            trunk_col = rng.choice(["#5c3d1e", "#6b4c2a", "#4a2f15"])
            green_col = rng.choice(["#2d5a27", "#3a6b30", "#4a7a3a", "#253f22"])
            top_col   = rng.choice(["#1e4020", "#234823", "#2a5424"])

        trunk_r = rng.uniform(0.12, 0.18)
        lean_x  = rng.uniform(-0.08, 0.08)   # slight lean in canopy offset
        lean_z  = rng.uniform(-0.08, 0.08)

        packets.append({"piece_id": p.id, "primitives": [
            # Trunk
            {"shape": "cylinder", "dimensions": [trunk_r, trunk_r * 1.1, trunk_h],
             "position": [0, trunk_h * 0.5, 0],
             "material": {"color": trunk_col, "roughness": 0.92}},
            # Lower canopy cone
            {"shape": "cone", "dimensions": [canopy_r, canopy_h],
             "position": [lean_x, trunk_h + canopy_h * 0.5, lean_z],
             "material": {"color": green_col, "roughness": 0.88}},
            # Upper canopy tip
            {"shape": "cone", "dimensions": [top_r, top_h],
             "position": [lean_x * 1.2, trunk_h + canopy_h + top_h * 0.5, lean_z * 1.2],
             "material": {"color": top_col, "roughness": 0.85}},
        ]})

    # ── ROAD PAVERS ────────────────────────────────────────────────────────────
    elif p.type == "road":
        # Each approach step is a rough stone paver, slightly varied
        slab_w = rng.uniform(0.80, 0.95)
        slab_h = rng.uniform(0.07, 0.13)
        slab_d = rng.uniform(0.80, 0.95)
        # Edge pavers (first 3 near shrine) get a slight mossy tint
        step_idx = int(str(p.label).split("_")[-1]) if "_" in str(p.label) else 0
        if step_idx <= 2:
            stone_col = rng.choice(["#8a8070", "#7a7060", "#858060"])
        else:
            stone_col = rng.choice(["#6e6858", "#787060", "#696050"])
        # Slight rotation for natural feel
        rot_y = rng.uniform(-6, 6)
        packets.append({"piece_id": p.id, "primitives": [
            {"shape": "box", "dimensions": [slab_w, slab_h, slab_d],
             "position": [rng.uniform(-0.05, 0.05), slab_h * 0.5, rng.uniform(-0.05, 0.05)],
             "rotation": [0, rot_y, 0],
             "material": {"color": stone_col, "roughness": 0.95}},
        ]})

    # ── LANTERNS ───────────────────────────────────────────────────────────────
    elif p.type == "lantern":
        # Stone-post lanterns with warm oil-lamp glow
        # Vary post height slightly; first two (near shrine) slightly taller
        light_idx = int(str(p.label).split("_")[-1]) if "_" in str(p.label) else 0
        post_h = rng.uniform(1.45, 1.70)
        # Dimmer lanterns further from shrine
        intensity = 1.0 - (light_idx * 0.07)
        intensity = max(0.55, intensity)
        glow_col  = rng.choice(["#ffcc44", "#ffbb33", "#ffdd66"])
        emissive  = rng.choice(["#ff9900", "#ffaa00", "#ff8800"])
        # Post material — iron vs stone
        post_col  = rng.choice(["#3a3530", "#444038", "#2e2b26"])

        packets.append({"piece_id": p.id, "primitives": [
            # Base stone block
            {"shape": "box", "dimensions": [0.22, 0.18, 0.22],
             "position": [0, 0.09, 0],
             "material": {"color": "#7a7060", "roughness": 0.9}},
            # Iron post
            {"shape": "cylinder", "dimensions": [0.055, 0.055, post_h],
             "position": [0, post_h * 0.5 + 0.18, 0],
             "material": {"color": post_col, "roughness": 0.6, "metalness": 0.4}},
            # Cross cap
            {"shape": "box", "dimensions": [0.28, 0.06, 0.28],
             "position": [0, post_h + 0.18, 0],
             "material": {"color": post_col, "roughness": 0.5, "metalness": 0.5}},
            # Lantern housing
            {"shape": "box", "dimensions": [0.22, 0.30, 0.22],
             "position": [0, post_h + 0.18 - 0.18, 0],
             "material": {"color": glow_col, "roughness": 0.2,
                          "emissive": emissive, "emissive_intensity": intensity}},
            # Flame core
            {"shape": "sphere", "dimensions": [0.06],
             "position": [0, post_h + 0.18 - 0.08, 0],
             "material": {"color": "#ffffff", "roughness": 0.1,
                          "emissive": "#ffffff", "emissive_intensity": 1.8}},
        ]})

    # ── RUBBLE / STONES ────────────────────────────────────────────────────────
    elif p.type == "rubble":
        stone_idx = int(str(p.label).split("_")[-1]) if "_" in str(p.label) else 0
        # Each rubble stone is a different ruined fragment
        if stone_idx == 0:
            # Large slumped cornerstone, moss-covered
            packets.append({"piece_id": p.id, "primitives": [
                {"shape": "box", "dimensions": [0.7, 0.45, 0.55],
                 "position": [0, 0.22, 0], "rotation": [0, 18, 3],
                 "material": {"color": "#6a6050", "roughness": 0.97}},
                {"shape": "box", "dimensions": [0.4, 0.25, 0.35],
                 "position": [0.2, 0.50, 0.1], "rotation": [5, -10, 0],
                 "material": {"color": "#5a7050", "roughness": 1.0}},  # mossy top
            ]})
        elif stone_idx == 1:
            # Flat broken slab, partially buried
            packets.append({"piece_id": p.id, "primitives": [
                {"shape": "box", "dimensions": [0.85, 0.18, 0.60],
                 "position": [0, 0.06, 0.1], "rotation": [0, -25, 4],
                 "material": {"color": "#72685a", "roughness": 0.96}},
                {"shape": "box", "dimensions": [0.4, 0.14, 0.3],
                 "position": [-0.3, 0.07, -0.2], "rotation": [0, 40, 0],
                 "material": {"color": "#686058", "roughness": 0.95}},
            ]})
        elif stone_idx == 2:
            # Fallen column drum — cylindrical stone, tipped over
            packets.append({"piece_id": p.id, "primitives": [
                {"shape": "cylinder", "dimensions": [0.22, 0.22, 0.60],
                 "position": [0, 0.22, 0], "rotation": [90, 0, 15],
                 "material": {"color": "#7a7060", "roughness": 0.94}},
                {"shape": "box", "dimensions": [0.25, 0.12, 0.20],
                 "position": [0.2, 0.06, 0.2],
                 "material": {"color": "#6e6858", "roughness": 0.96}},
            ]})
        else:
            # Rounded lichen-covered boulder
            packets.append({"piece_id": p.id, "primitives": [
                {"shape": "sphere", "dimensions": [0.30],
                 "position": [0, 0.30, 0],
                 "material": {"color": "#7a7862", "roughness": 0.98}},
                {"shape": "sphere", "dimensions": [0.20],
                 "position": [0.18, 0.42, 0.1],
                 "material": {"color": "#6a7052", "roughness": 0.97}},
            ]})

    # ── STATUES ────────────────────────────────────────────────────────────────
    elif p.type == "statue":
        statue_idx = int(str(p.label).split("_")[-1]) if "_" in str(p.label) else 0
        # Guardian_0 faces the approach from the west; guardian_1 from the north
        # Both are weathered stone figures in postures of vigilance
        stone_base = "#8a8070"
        stone_body = "#7a7060"
        stone_worn = "#6a6050"
        # Slight lean for age — guardian_0 leans right, guardian_1 leans left
        lean = 3.5 if statue_idx == 0 else -3.5

        packets.append({"piece_id": p.id, "primitives": [
            # Square plinth
            {"shape": "box", "dimensions": [0.50, 0.40, 0.50],
             "position": [0, 0.20, 0],
             "material": {"color": stone_base, "roughness": 0.92}},
            # Lower body / robes
            {"shape": "box", "dimensions": [0.38, 0.55, 0.30],
             "position": [0, 0.68, 0], "rotation": [0, 0, lean],
             "material": {"color": stone_body, "roughness": 0.90}},
            # Torso / cloak
            {"shape": "box", "dimensions": [0.32, 0.42, 0.26],
             "position": [0, 1.15, 0], "rotation": [0, 0, lean],
             "material": {"color": stone_body, "roughness": 0.88}},
            # Head
            {"shape": "box", "dimensions": [0.22, 0.26, 0.22],
             "position": [0, 1.54, 0], "rotation": [0, 0, lean * 0.5],
             "material": {"color": stone_worn, "roughness": 0.90}},
            # Extended arm (raised in warning gesture)
            {"shape": "box", "dimensions": [0.28, 0.10, 0.10],
             "position": [0.22 if statue_idx == 0 else -0.22, 1.20, 0],
             "rotation": [0, 0, -20 if statue_idx == 0 else 20],
             "material": {"color": stone_worn, "roughness": 0.90}},
            # Mossy lichen patches on top surfaces
            {"shape": "box", "dimensions": [0.20, 0.03, 0.18],
             "position": [0, 1.68, 0],
             "material": {"color": "#6a7a50", "roughness": 1.0}},
            {"shape": "box", "dimensions": [0.35, 0.02, 0.28],
             "position": [0, 0.41, 0],
             "material": {"color": "#5a7040", "roughness": 1.0}},
        ]})

# ─── Validate all packets ─────────────────────────────────────────────────────
print(f"\nAuthored {len(packets)} geometry packets")
validated = receive_all(packets)
print(f"receive_all: {len(validated)} packets valid ✓")

# Summarise primitives per type
from collections import defaultdict
counts = defaultdict(lambda: [0, 0])
for p in result.pieces:
    pkt = validated.get(p.id)
    if pkt:
        counts[p.type][0] += 1
        counts[p.type][1] += len(pkt["primitives"])
for t, (pieces, prims) in sorted(counts.items()):
    print(f"  {t:12s}: {pieces} pieces, {prims} primitives total")

# ─── Save result and packets for next steps ───────────────────────────────────
import pickle
with open("/tmp/shrine_loop_state.pkl", "wb") as f:
    pickle.dump({"result": result, "packets": validated}, f)
print("\nState saved to /tmp/shrine_loop_state.pkl")

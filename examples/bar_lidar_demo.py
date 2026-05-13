"""
Bar interior: full protocol path → equirectangular 360° lidar panorama.
Demonstrates the equirectangular lens from lidar_lenses.py on an interior scene.
"""
import sys, os, random, json, pickle
sys.path.insert(0, 'scripts')

from dropgrid.api import solve_object_scene
from authoring.context_exporter import export_all_contexts
from authoring.geometry_receiver import receive_all
from verification.lidar_lenses import (
    primitives_from_scene, Primitive, Camera, fire_burst,
    fuse_bursts_attention, make_rotation_matrix
)
import numpy as np
from PIL import Image

# ─── DSL ──────────────────────────────────────────────────────────────────────
DSL = """
anchor counter bar_counter
ma hard radius 3
object stool   label stools   count 7  target bar_counter side any distance 1 spacing 1
object shelf   label shelves  count 2  near bar_counter radius 2
object table   label tables   count 4  shape scatter radius 6
object chair   label chairs   count 10 target tables side any distance 1 spacing 1
object barrel  label kegs     count 4  shape circle radius 7 arc 0.12
object torch   label torches  count 8  shape scatter radius 8
"""

result = solve_object_scene(DSL, seed=13)
contexts = export_all_contexts(result)
print(f"Solver: {len(result.pieces)} pieces placed")

# ─── Authoring ────────────────────────────────────────────────────────────────
packets = []
for p in result.pieces:
    ctx = contexts[p.id]
    near_path = ctx.get("near_path", False)
    rng = random.Random(p.id * 97 + 17)

    # ── BAR COUNTER ──────────────────────────────────────────────────────────
    if p.type == "counter":
        packets.append({"piece_id": p.id, "primitives": [
            # Main bar body — solid dark wood
            {"shape": "box", "dimensions": [2.0, 1.1, 1.0],
             "position": [0, 0.55, 0],
             "material": {"color": "#3a2210", "roughness": 0.6}},
            # Bar top — lighter polished surface
            {"shape": "box", "dimensions": [2.2, 0.08, 1.1],
             "position": [0, 1.14, 0],
             "material": {"color": "#5c3a18", "roughness": 0.3, "metalness": 0.05}},
            # Foot rail — iron rod at base
            {"shape": "cylinder", "dimensions": [0.04, 0.04, 1.9],
             "position": [0, 0.18, 0.55], "rotation": [0, 90, 0],
             "material": {"color": "#2a2520", "roughness": 0.4, "metalness": 0.6}},
        ]})

    # ── SHELF / BACK BAR ─────────────────────────────────────────────────────
    elif p.type == "shelf":
        shelf_idx = int(str(p.label).split("_")[-1])
        y_low  = 1.3 + shelf_idx * 0.55
        # Shelf board
        packets.append({"piece_id": p.id, "primitives": [
            {"shape": "box", "dimensions": [1.2, 0.06, 0.25],
             "position": [0, y_low, 0],
             "material": {"color": "#3a2210", "roughness": 0.5}},
            # 3 bottles on shelf
            {"shape": "cylinder", "dimensions": [0.07, 0.05, 0.28],
             "position": [-0.35, y_low + 0.20, 0],
             "material": {"color": "#2a5a30", "roughness": 0.2, "metalness": 0.1}},
            {"shape": "cylinder", "dimensions": [0.07, 0.05, 0.32],
             "position": [0.0,  y_low + 0.22, 0],
             "material": {"color": "#8a4020", "roughness": 0.15, "metalness": 0.1}},
            {"shape": "cylinder", "dimensions": [0.07, 0.05, 0.25],
             "position": [0.35, y_low + 0.19, 0],
             "material": {"color": "#1a3050", "roughness": 0.2, "metalness": 0.15}},
        ]})

    # ── TABLE ────────────────────────────────────────────────────────────────
    elif p.type == "table":
        leg_col = rng.choice(["#3a2210", "#4a2d18", "#2e1a0c"])
        top_col = rng.choice(["#5c3a18", "#4e3012", "#6a4020"])
        table_r = rng.uniform(0.50, 0.65)
        packets.append({"piece_id": p.id, "primitives": [
            # Table top — round
            {"shape": "cylinder", "dimensions": [table_r, table_r, 0.07],
             "position": [0, 0.78, 0],
             "material": {"color": top_col, "roughness": 0.5}},
            # Central pedestal leg
            {"shape": "cylinder", "dimensions": [0.06, 0.08, 0.76],
             "position": [0, 0.38, 0],
             "material": {"color": leg_col, "roughness": 0.7}},
            # Foot spread
            {"shape": "cylinder", "dimensions": [0.25, 0.20, 0.06],
             "position": [0, 0.03, 0],
             "material": {"color": leg_col, "roughness": 0.8}},
            # Candle on table
            {"shape": "cylinder", "dimensions": [0.04, 0.04, 0.14],
             "position": [rng.uniform(-0.15, 0.15), 0.89, rng.uniform(-0.15, 0.15)],
             "material": {"color": "#f0e8c8", "roughness": 0.9}},
            {"shape": "sphere", "dimensions": [0.04],
             "position": [rng.uniform(-0.15, 0.15), 1.04, rng.uniform(-0.15, 0.15)],
             "material": {"color": "#ffee88", "roughness": 0.4,
                          "emissive": "#ffcc44", "emissive_intensity": 0.9}},
        ]})

    # ── BARREL / KEG ─────────────────────────────────────────────────────────
    elif p.type == "barrel":
        wood_col  = rng.choice(["#5a3a1a", "#4a3010", "#6a4020"])
        hoop_col  = "#2a2520"
        h = rng.uniform(0.60, 0.75)
        r_mid = rng.uniform(0.22, 0.28)
        r_end = r_mid * 0.80
        packets.append({"piece_id": p.id, "primitives": [
            # Barrel body
            {"shape": "cylinder", "dimensions": [r_mid, r_mid, h],
             "position": [0, h * 0.5, 0],
             "material": {"color": wood_col, "roughness": 0.85}},
            # Top hoop
            {"shape": "cylinder", "dimensions": [r_mid + 0.02, r_mid + 0.02, 0.04],
             "position": [0, h * 0.82, 0],
             "material": {"color": hoop_col, "roughness": 0.5, "metalness": 0.6}},
            # Mid hoop
            {"shape": "cylinder", "dimensions": [r_mid + 0.03, r_mid + 0.03, 0.05],
             "position": [0, h * 0.50, 0],
             "material": {"color": hoop_col, "roughness": 0.5, "metalness": 0.6}},
            # Bottom hoop
            {"shape": "cylinder", "dimensions": [r_mid + 0.02, r_mid + 0.02, 0.04],
             "position": [0, h * 0.18, 0],
             "material": {"color": hoop_col, "roughness": 0.5, "metalness": 0.6}},
        ]})

    # ── TORCH ────────────────────────────────────────────────────────────────
    elif p.type == "torch":
        # Wall-mount torch — bracket + shaft + flame
        packets.append({"piece_id": p.id, "primitives": [
            # Wooden shaft
            {"shape": "cylinder", "dimensions": [0.04, 0.04, 0.50],
             "position": [0, 0.25, 0], "rotation": [15, 0, 0],
             "material": {"color": "#4a2e10", "roughness": 0.9}},
            # Metal bracket
            {"shape": "box", "dimensions": [0.12, 0.06, 0.12],
             "position": [0, 0.08, 0],
             "material": {"color": "#2a2520", "roughness": 0.5, "metalness": 0.5}},
            # Flame head
            {"shape": "sphere", "dimensions": [0.09],
             "position": [0, 0.58, -0.06],
             "material": {"color": "#ffaa22", "roughness": 0.5,
                          "emissive": "#ff7700", "emissive_intensity": 1.5}},
            # Glow halo
            {"shape": "sphere", "dimensions": [0.16],
             "position": [0, 0.58, -0.06],
             "material": {"color": "#ff4400", "roughness": 1.0,
                          "emissive": "#ff2200", "emissive_intensity": 0.4}},
        ]})

# ─── Validate ─────────────────────────────────────────────────────────────────
validated = receive_all(packets)
print(f"receive_all: {len(validated)} packets valid ✓")

# ─── Build lidar primitives from solver + explicit room walls ─────────────────
packets_list = list(validated.values())
scene_prims = primitives_from_scene(result, packets_list)

# Scene centroid (for offsetting room walls)
pieces = result.pieces
cx = sum(p.gx for p in pieces) / len(pieces)
cz = sum(p.gz for p in pieces) / len(pieces)
# primitives_from_scene centers to (0,0,0), so room walls go around origin
# Scene spans roughly ±9 units from centroid
ROOM_HALF = 9.5
ROOM_H    = 3.8
WALL_T    = 0.25
CEIL_H    = ROOM_H
WALL_COL  = (0.32, 0.22, 0.12)   # dark wood panels, RGB float
CEIL_COL  = (0.18, 0.14, 0.10)
FLOOR_COL = (0.25, 0.18, 0.10)
I3 = np.eye(3)

def wall_prim(center, half, color):
    return Primitive(
        shape="box", center=np.array(center, float),
        half_extents=np.array(half, float),
        rotation_matrix=I3, inv_rotation_matrix=I3,
        color=color, piece_id=-1, piece_type="wall",
    )

room_walls = [
    # North wall
    wall_prim([0, ROOM_H/2, -ROOM_HALF], [ROOM_HALF, ROOM_H/2, WALL_T], WALL_COL),
    # South wall
    wall_prim([0, ROOM_H/2,  ROOM_HALF], [ROOM_HALF, ROOM_H/2, WALL_T], WALL_COL),
    # West wall
    wall_prim([-ROOM_HALF, ROOM_H/2, 0], [WALL_T, ROOM_H/2, ROOM_HALF], WALL_COL),
    # East wall
    wall_prim([ ROOM_HALF, ROOM_H/2, 0], [WALL_T, ROOM_H/2, ROOM_HALF], WALL_COL),
    # Ceiling
    wall_prim([0, CEIL_H, 0], [ROOM_HALF, WALL_T, ROOM_HALF], CEIL_COL),
    # Floor (thin slab so normals point up)
    wall_prim([0, -0.08, 0], [ROOM_HALF, 0.08, ROOM_HALF], FLOOR_COL),
]

all_prims = scene_prims + room_walls
print(f"Total lidar primitives: {len(all_prims)} ({len(scene_prims)} scene + {len(room_walls)} room)")

# ─── Equirectangular panorama from bar-stool height at center ─────────────────
os.makedirs("examples/bar_lidar", exist_ok=True)

# Camera at bar-stool height, slightly toward seating area
cam_equirect = Camera(
    position=np.array([0.0, 1.25, 2.5]),   # centered, looking into the room
    target=np.array([0.0, 1.25, 0.0]),
    lens="equirectangular",
    width=1200, height=600,
)
print("Firing equirectangular panorama (360°×180°)...")
burst_eq = fire_burst(cam_equirect, all_prims, n_samples=80000, seed=42)
img_eq, conf_eq = fuse_bursts_attention([burst_eq], cam_equirect)
img_eq.save("examples/bar_lidar/equirect_panorama.png")
print(f"  coverage={burst_eq.coverage:.2%}, pieces={burst_eq.unique_pieces}/{len(result.pieces)}")
print("  Saved: examples/bar_lidar/equirect_panorama.png")

# ─── Fisheye from counter looking into the seating area ─────────────────────
cam_fish = Camera(
    position=np.array([0.0, 1.5, -1.0]),   # behind the bar, looking out
    target=np.array([0.0, 1.2, 4.0]),
    lens="fisheye", fisheye_fov_deg=200,
    width=700, height=700,
)
print("Firing fisheye (200° FOV, bartender view)...")
burst_fish = fire_burst(cam_fish, all_prims, n_samples=60000, seed=7)
img_fish, conf_fish = fuse_bursts_attention([burst_fish], cam_fish)
img_fish.save("examples/bar_lidar/fisheye_bartender.png")
print(f"  coverage={burst_fish.coverage:.2%}, pieces={burst_fish.unique_pieces}/{len(result.pieces)}")
print("  Saved: examples/bar_lidar/fisheye_bartender.png")

# ─── Confidence heatmap for equirect ────────────────────────────────────────
conf_eq.save("examples/bar_lidar/equirect_confidence.png")
print("  Confidence map: examples/bar_lidar/equirect_confidence.png")

print("\nDone.")

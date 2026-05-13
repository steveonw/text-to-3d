"""
lidar_lenses.py — standalone single-file engine (v0.2.0)

Multi-lens analytic raycaster with attention-weighted fusion, triangle
mesh support, BVH acceleration, and STL loading. Pure numpy + PIL.
Drop this single file into any sandbox; no package install needed.

Original, intersection routines, BVH, scene
loading, rendering. Pure numpy + PIL.

v0.2.0 additions over v3:
  - Triangle meshes (Mesh dataclass) with vectorized Möller-Trumbore intersection
  - Two-level BVH acceleration (top-level over scene items + per-mesh over triangles)
  - Scene dataclass holding primitives + meshes + cached BVH
  - STL loader (binary + ASCII) for importing arbitrary 3D models
  - Frustum culling helpers for pinhole cameras

The cast_rays API accepts either a list of Primitives (legacy) or a Scene
(new). When given a list, it wraps in a Scene and builds a BVH transparently.
"""
import math
import struct
from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageDraw


# ──────────────────────────────────────────────────────────
# PRIMITIVE STORAGE (unchanged from v2)
# ──────────────────────────────────────────────────────────
@dataclass
class Primitive:
    shape: str
    center: np.ndarray
    half_extents: np.ndarray
    rotation_matrix: np.ndarray
    inv_rotation_matrix: np.ndarray
    color: Tuple[float, float, float]
    piece_id: int
    piece_type: str


def hex_to_rgb(h: str) -> Tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def make_rotation_matrix(rx_deg: float, ry_deg: float, rz_deg: float) -> np.ndarray:
    cx, sx = math.cos(math.radians(rx_deg)), math.sin(math.radians(rx_deg))
    cy, sy = math.cos(math.radians(ry_deg)), math.sin(math.radians(ry_deg))
    cz, sz = math.cos(math.radians(rz_deg)), math.sin(math.radians(rz_deg))
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def primitives_from_scene(result, packets) -> List[Primitive]:
    pieces = result.pieces
    if pieces:
        cx_c = sum(p.gx for p in pieces) / len(pieces)
        cz_c = sum(p.gz for p in pieces) / len(pieces)
    else:
        cx_c = cz_c = 0.0
    piece_by_id = {p.id: p for p in pieces}
    piece_type_by_id = {p.id: p.type for p in pieces}

    prims: List[Primitive] = []
    for pkt in packets:
        piece = piece_by_id.get(pkt["piece_id"])
        if piece is None:
            continue
        px = piece.gx - cx_c
        pz = piece.gz - cz_c
        py = 0.0
        for prim in pkt["primitives"]:
            shape = prim["shape"]
            local_pos = np.array(prim["position"], dtype=np.float64)
            rot_deg = prim.get("rotation", [0, 0, 0])
            R = make_rotation_matrix(*rot_deg)
            world_center = np.array([px, py, pz]) + local_pos
            dims = prim["dimensions"]
            if shape == "box":
                half = np.array([dims[0]/2, dims[1]/2, dims[2]/2])
            elif shape == "cylinder":
                r = dims[1] if len(dims) > 1 else dims[0]
                h = dims[2] if len(dims) > 2 else dims[1]
                half = np.array([r, h/2, 0.0])
            elif shape == "sphere":
                r = dims[0]
                half = np.array([r, r, r])
            else:
                continue
            mat = prim.get("material", {})
            color = hex_to_rgb(mat.get("color", "#888888"))
            prims.append(Primitive(
                shape=shape, center=world_center, half_extents=half,
                rotation_matrix=R.T, inv_rotation_matrix=R,
                color=color, piece_id=pkt["piece_id"],
                piece_type=piece_type_by_id.get(pkt["piece_id"], "?"),
            ))
    return prims


# ──────────────────────────────────────────────────────────
# RAY-PRIMITIVE INTERSECTION
# ──────────────────────────────────────────────────────────
INF = 1e9
EPS = 1e-9


def _safe_inverse(d: np.ndarray) -> np.ndarray:
    sign = np.where(d >= 0, 1.0, -1.0)
    safe = np.where(np.abs(d) < EPS, sign * EPS, d)
    return 1.0 / safe


def ray_box_local(origins: np.ndarray, dirs: np.ndarray,
                  half: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Slab method, with argmin/argmax for the chosen-axis normal (v3 polish)."""
    inv = _safe_inverse(dirs)
    t1 = (-half - origins) * inv
    t2 = ( half - origins) * inv
    tmin_per_axis = np.minimum(t1, t2)
    tmax_per_axis = np.maximum(t1, t2)
    t_near = tmin_per_axis.max(axis=1)
    t_far  = tmax_per_axis.min(axis=1)
    hit = (t_far > t_near) & (t_far > EPS)
    use_far = (t_near <= EPS) & hit
    t = np.where(use_far, t_far, t_near)

    # Axis index that gave the chosen t (argmax for near, argmin for far)
    axis_near = np.argmax(tmin_per_axis, axis=1)
    axis_far  = np.argmin(tmax_per_axis, axis=1)
    axis = np.where(use_far, axis_far, axis_near)

    hit_pt = origins + dirs * t[:, None]
    normal = np.zeros_like(origins)
    rows = np.arange(len(origins))
    sign = np.sign(hit_pt[rows, axis])
    sign = np.where(sign == 0, 1.0, sign)
    normal[rows, axis] = np.where(hit, sign, 0.0)
    return np.where(hit, t, INF), normal


def ray_cylinder_local(origins: np.ndarray, dirs: np.ndarray,
                       r: float, half_h: float) -> Tuple[np.ndarray, np.ndarray]:
    """v3: test both side roots independently — fixes the t_side2 fallback bug."""
    ox, oy, oz = origins[:, 0], origins[:, 1], origins[:, 2]
    dx, dy, dz = dirs[:, 0], dirs[:, 1], dirs[:, 2]

    # Side surface — both roots tested
    a = dx*dx + dz*dz
    b = 2 * (ox*dx + oz*dz)
    c = ox*ox + oz*oz - r*r
    disc = b*b - 4*a*c
    valid = (disc >= 0) & (a > EPS)
    sqrt_disc = np.sqrt(np.where(disc < 0, 0, disc))
    a_safe = np.where(a < EPS, 1.0, a)
    t_s1 = (-b - sqrt_disc) / (2 * a_safe)
    t_s2 = (-b + sqrt_disc) / (2 * a_safe)
    y_s1 = oy + dy * t_s1
    y_s2 = oy + dy * t_s2
    s1_ok = valid & (t_s1 > EPS) & (np.abs(y_s1) <= half_h)
    s2_ok = valid & (t_s2 > EPS) & (np.abs(y_s2) <= half_h)
    t_s1_f = np.where(s1_ok, t_s1, INF)
    t_s2_f = np.where(s2_ok, t_s2, INF)
    t_side_final = np.minimum(t_s1_f, t_s2_f)

    # Caps
    dy_safe = np.where(np.abs(dy) < EPS, np.where(dy >= 0, EPS, -EPS), dy)
    t_top = (half_h - oy) / dy_safe
    t_bot = (-half_h - oy) / dy_safe

    def cap_hit(t_cap):
        x_at = ox + dx * t_cap
        z_at = oz + dz * t_cap
        return (x_at*x_at + z_at*z_at <= r*r) & (t_cap > EPS) & (np.abs(dy) > EPS)

    top_ok = cap_hit(t_top)
    bot_ok = cap_hit(t_bot)
    t_top_f = np.where(top_ok, t_top, INF)
    t_bot_f = np.where(bot_ok, t_bot, INF)

    t_all = np.stack([t_side_final, t_top_f, t_bot_f], axis=1)
    winner = np.argmin(t_all, axis=1)
    t_min = t_all[np.arange(len(t_all)), winner]

    normal = np.zeros_like(origins)
    is_side = (winner == 0) & (t_min < INF)
    if is_side.any():
        xh = ox[is_side] + dx[is_side] * t_min[is_side]
        zh = oz[is_side] + dz[is_side] * t_min[is_side]
        n_xz = np.stack([xh, np.zeros_like(xh), zh], axis=1)
        n_xz = n_xz / np.linalg.norm(n_xz, axis=1, keepdims=True).clip(EPS)
        normal[is_side] = n_xz
    normal[(winner == 1) & (t_min < INF), 1] =  1.0
    normal[(winner == 2) & (t_min < INF), 1] = -1.0
    return t_min, normal


def ray_sphere(origins: np.ndarray, dirs: np.ndarray,
               center: np.ndarray, radius: float) -> Tuple[np.ndarray, np.ndarray]:
    oc = origins - center
    a = (dirs * dirs).sum(axis=1)
    b = 2 * (dirs * oc).sum(axis=1)
    c = (oc * oc).sum(axis=1) - radius*radius
    disc = b*b - 4*a*c
    valid = disc >= 0
    sqrt_disc = np.sqrt(np.where(disc < 0, 0, disc))
    a_safe = np.where(a < EPS, 1.0, a)
    t1 = (-b - sqrt_disc) / (2 * a_safe)
    t2 = (-b + sqrt_disc) / (2 * a_safe)
    t = np.where(t1 > EPS, t1, t2)
    hit = valid & (t > EPS)
    normal = np.zeros_like(origins)
    if hit.any():
        hit_pt = origins[hit] + dirs[hit] * t[hit, None]
        n = hit_pt - center
        n = n / np.linalg.norm(n, axis=1, keepdims=True).clip(EPS)
        normal[hit] = n
    return np.where(hit, t, INF), normal


def cast_rays(origins, dirs, prims):
    N = len(origins)
    best_t = np.full(N, INF)
    best_color = np.zeros((N, 3))
    best_normal = np.zeros((N, 3))
    best_pid = np.full(N, -1, dtype=np.int64)
    for prim in prims:
        if prim.shape == "sphere":
            t, normal = ray_sphere(origins, dirs, prim.center, prim.half_extents[0])
        else:
            o_local = (origins - prim.center) @ prim.rotation_matrix.T
            d_local = dirs @ prim.rotation_matrix.T
            if prim.shape == "box":
                t, n_local = ray_box_local(o_local, d_local, prim.half_extents)
            elif prim.shape == "cylinder":
                t, n_local = ray_cylinder_local(
                    o_local, d_local,
                    r=float(prim.half_extents[0]),
                    half_h=float(prim.half_extents[1]),
                )
            else:
                continue
            normal = n_local @ prim.inv_rotation_matrix.T
        color = np.array(prim.color)
        closer = t < best_t
        best_t = np.where(closer, t, best_t)
        best_color[closer] = color
        best_normal[closer] = normal[closer]
        best_pid[closer] = prim.piece_id
    return best_t, best_color, best_normal, best_pid


# ──────────────────────────────────────────────────────────
# CAMERA / BURST (unchanged from v2)
# ──────────────────────────────────────────────────────────
@dataclass
class Camera:
    """Camera with selectable lens. Field semantics vary by lens:
        - pinhole:        fov_deg = total VERTICAL FOV (horizontal scales by aspect)
        - fisheye:        fisheye_fov_deg = total angular coverage (180 = full hemi);
                          returns ≤ n_samples rays (corners outside the lens
                          circle are dropped; ~78% retention for square images)
        - orthographic:   ortho_size = half-width of view frame in world units;
                          content outside ±ortho_size is silently clipped
        - equirectangular: ignores fov/ortho; full 360°×180° sphere
        - telephoto:      pinhole with narrow fov_deg (≤15)
    """
    position: np.ndarray
    target: np.ndarray
    up: np.ndarray = field(default_factory=lambda: np.array([0., 1., 0.]))
    fov_deg: float = 60.0
    width: int = 600
    height: int = 400
    lens: str = "pinhole"
    fisheye_fov_deg: float = 180.0
    ortho_size: float = 8.0


def _camera_basis(cam: Camera):
    forward = cam.target - cam.position
    forward = forward / np.linalg.norm(forward)
    right = np.cross(forward, cam.up)
    rn = np.linalg.norm(right)
    if rn < EPS:
        right = np.cross(forward, np.array([0., 0., 1.]))
        right = right / np.linalg.norm(right)
    else:
        right = right / rn
    up = np.cross(right, forward)
    return forward, right, up


def stratified_rays(cam, n_samples, rng):
    W, H = cam.width, cam.height
    aspect = W / H
    fov_rad = math.radians(cam.fov_deg)
    half_h = math.tan(fov_rad / 2)
    half_w = half_h * aspect
    grid_w = max(1, int(math.sqrt(n_samples * aspect)))
    grid_h = max(1, n_samples // grid_w)
    gx, gy = np.meshgrid(np.arange(grid_w), np.arange(grid_h))
    jx = rng.random(gx.shape); jy = rng.random(gy.shape)
    px = ((gx + jx) / grid_w * W).flatten()
    py = ((gy + jy) / grid_h * H).flatten()
    ndc_x = (px / W - 0.5) * 2 * half_w
    ndc_y = (0.5 - py / H) * 2 * half_h
    forward, right, up = _camera_basis(cam)
    dirs = (forward[None, :]
            + ndc_x[:, None] * right[None, :]
            + ndc_y[:, None] * up[None, :])
    dirs = dirs / np.linalg.norm(dirs, axis=1, keepdims=True)
    origins = np.tile(cam.position[None, :], (len(dirs), 1))
    pixels = np.stack([px, py], axis=1)
    return origins, dirs, pixels


@dataclass
class Burst:
    cam: Camera
    pixels: np.ndarray
    origins: np.ndarray       # per-ray origins (lens-aware; for ortho they differ)
    dirs: np.ndarray
    depths: np.ndarray
    colors: np.ndarray
    normals: np.ndarray
    piece_ids: np.ndarray
    coverage: float = 0.0
    unique_pieces: int = 0
    pilot_score: float = 1.0


def fire_burst(cam, prims, n_samples, seed):
    rng = np.random.default_rng(seed)
    origins, dirs, pixels = stratified_rays(cam, n_samples, rng)
    t, color, normal, pid = cast_rays(origins, dirs, prims)
    hit = t < INF
    coverage = float(hit.mean()) if len(t) else 0.0
    unique_pieces = int(len(np.unique(pid[hit]))) if hit.any() else 0
    return Burst(
        cam=cam, pixels=pixels, origins=origins, dirs=dirs, depths=t, colors=color,
        normals=normal, piece_ids=pid,
        coverage=coverage, unique_pieces=unique_pieces,
    )


# ──────────────────────────────────────────────────────────
# RENDERING
# ──────────────────────────────────────────────────────────
def depth_to_color(depths, near, far):
    d = np.clip((depths - near) / (far - near + EPS), 0, 1)
    r = np.clip(1 - 2*d, 0, 1)
    g = np.clip(1 - np.abs(2*d - 1), 0, 1)
    b = np.clip(2*d - 1, 0, 1)
    return np.stack([r, g, b], axis=1)


def render_burst(burst, mode="lidar", near=0.5, far=20.0,
                 bg="#08101a", dot_size=1, auto_calibrate=False):
    W, H = burst.cam.width, burst.cam.height
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)
    hit = burst.depths < INF
    if not hit.any():
        return img
    hit_depths = burst.depths[hit]
    if auto_calibrate and mode == "lidar":
        near = float(hit_depths.min()) - 0.1
        far = float(np.percentile(hit_depths, 95))
        if far - near < 0.5:
            far = near + 0.5

    px = burst.pixels[hit, 0].astype(int)
    py = burst.pixels[hit, 1].astype(int)
    if mode == "lidar":
        cols = depth_to_color(hit_depths, near, far)
    elif mode == "material":
        cols = burst.colors[hit]
    elif mode == "shaded":
        light = np.array([0.4, 0.7, 0.3]); light /= np.linalg.norm(light)
        ndotl = np.clip((burst.normals[hit] * light).sum(axis=1), 0.2, 1.0)
        cols = burst.colors[hit] * ndotl[:, None]
    else:
        cols = burst.colors[hit]

    cols_int = (np.clip(cols, 0, 1) * 255).astype(np.uint8)
    for i in range(len(px)):
        x, y = int(px[i]), int(py[i])
        if 0 <= x < W and 0 <= y < H:
            c = tuple(int(v) for v in cols_int[i])
            if dot_size == 1:
                img.putpixel((x, y), c)
            else:
                draw.ellipse([x - dot_size, y - dot_size,
                              x + dot_size, y + dot_size], fill=c)
    return img


# ──────────────────────────────────────────────────────────
# PILOT-AND-PRUNE (unchanged from v2)
# ──────────────────────────────────────────────────────────
def pilot_and_prune(cams, prims, pilot_samples=2000, keep_k=4, seed=42):
    pilots = [fire_burst(cam, prims, pilot_samples, seed + i)
              for i, cam in enumerate(cams)]
    scores = np.array([p.coverage + 0.15 * math.log(1 + p.unique_pieces) for p in pilots])
    for p, s in zip(pilots, scores):
        p.pilot_score = float(s)
    keep_idx = list(np.argsort(scores)[-keep_k:][::-1])
    return keep_idx, pilots


# ──────────────────────────────────────────────────────────
# FUSION
# ──────────────────────────────────────────────────────────
def _burst_world_points(b: Burst):
    hit = b.depths < INF
    if not hit.any():
        return (np.zeros((0, 3)), np.zeros((0, 3)),
                np.zeros((0, 3)), np.array([]), np.array([], dtype=int))
    hit_idx = np.where(hit)[0]
    # Use stored per-ray origins — correct for any source lens (pinhole shares
    # them; orthographic does not). Falls back to cam.position for legacy
    # Bursts that may not have origins stored (shouldn't happen post-fix).
    if hasattr(b, "origins") and b.origins is not None and len(b.origins):
        origins = b.origins[hit_idx]
    else:
        origins = b.cam.position[None, :].repeat(len(hit_idx), axis=0)
    pts = origins + b.dirs[hit_idx] * b.depths[hit_idx, None]
    return pts, b.colors[hit_idx], b.normals[hit_idx], b.depths[hit_idx], hit_idx


# NOTE: fuse_bursts_pointcloud, fuse_bursts_attention, and project_to_camera
# live in scene_lens.lenses (lens-aware versions). Import from there.


# Viridis approximation: black at 0 (no data), then standard viridis from
# dark purple → blue → cyan → green → yellow. Hardcoded 12 stops, lerped.
_VIRIDIS_STOPS = np.array([
    [0.000, 0.000, 0.000],   # 0.00 — black (no data)
    [0.267, 0.005, 0.329],   # 0.10 — dark purple
    [0.283, 0.141, 0.458],   # 0.20
    [0.254, 0.265, 0.530],   # 0.30
    [0.207, 0.372, 0.553],   # 0.40
    [0.164, 0.471, 0.558],   # 0.50
    [0.128, 0.567, 0.551],   # 0.60
    [0.135, 0.659, 0.518],   # 0.70
    [0.267, 0.749, 0.441],   # 0.80
    [0.478, 0.821, 0.318],   # 0.90
    [0.741, 0.873, 0.150],   # 0.95
    [0.993, 0.906, 0.144],   # 1.00 — bright yellow
])


def _confidence_heatmap(conf_arr: np.ndarray,
                        bg_rgb: Tuple[int, int, int] = (8, 16, 26),
                        smooth: bool = False) -> Image.Image:
    """Render a confidence array as a viridis-like heatmap."""
    H_max = conf_arr.max()
    if H_max < EPS:
        return Image.new("RGB", conf_arr.shape[::-1], bg_rgb)
    cf = conf_arr / H_max
    n_stops = len(_VIRIDIS_STOPS)
    stop_positions = np.linspace(0, 1, n_stops)

    # Vectorized lerp through the LUT
    out = np.zeros((*cf.shape, 3))
    for ch in range(3):
        out[..., ch] = np.interp(cf, stop_positions, _VIRIDIS_STOPS[:, ch])

    # Background where there was zero confidence
    out[cf == 0] = np.array(bg_rgb) / 255.0

    img = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))
    if smooth:
        from PIL import ImageFilter
        img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
    return img


def composite_grid(images, labels, cols=3, pad=8, label_h=24, bg="#0a0a0e"):
    if not images:
        return Image.new("RGB", (100, 100), bg)
    iw, ih = images[0].size
    rows = (len(images) + cols - 1) // cols
    W = cols * (iw + pad) + pad
    H = rows * (ih + label_h + pad) + pad
    sheet = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(sheet)
    for i, (img, label) in enumerate(zip(images, labels)):
        r, c = divmod(i, cols)
        x = pad + c * (iw + pad)
        y = pad + r * (ih + label_h + pad)
        sheet.paste(img, (x, y + label_h))
        draw.text((x + 4, y + 4), label, fill="#cce0e0")
    return sheet


# ══════════════════════════════════════════════════════════════════════════
# v0.2.0 ADDITIONS — Triangle meshes, BVH acceleration, Scene container
# ══════════════════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────
# TRIANGLE MESH
# ──────────────────────────────────────────────────────────
@dataclass
class Mesh:
    """Triangle mesh. Holds many triangles sharing a transform and material.

    Fields:
        vertices:     (N_v, 3) world-space vertex positions
        faces:        (N_f, 3) int — indices into vertices
        face_normals: (N_f, 3) — precomputed unit normals (auto if None at init)
        color:        single RGB tuple, applied to all faces (per-face colors
                      can be added later)
        piece_id, piece_type: same role as Primitive's fields

    The mesh stores its own internal BVH over its triangles, built lazily on
    first ray-cast.
    """
    vertices: np.ndarray
    faces: np.ndarray
    color: Tuple[float, float, float]
    piece_id: int
    piece_type: str = "mesh"
    face_normals: np.ndarray = None
    aabb_min: np.ndarray = None
    aabb_max: np.ndarray = None
    _bvh: object = None  # BVHNode, built lazily

    def __post_init__(self):
        self.vertices = np.asarray(self.vertices, dtype=np.float64)
        self.faces = np.asarray(self.faces, dtype=np.int64)
        if self.face_normals is None:
            self.face_normals = _compute_face_normals(self.vertices, self.faces)
        if self.aabb_min is None:
            self.aabb_min = self.vertices.min(axis=0)
            self.aabb_max = self.vertices.max(axis=0)


def _compute_face_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Per-face unit normals via cross product of two edges."""
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]
    n = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(n, axis=1, keepdims=True).clip(EPS)
    return n / norms


def _triangle_aabbs(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """AABB for each triangle: (N_f, 2, 3) where [...,0]=min, [...,1]=max."""
    v = vertices[faces]  # (N_f, 3, 3)
    return np.stack([v.min(axis=1), v.max(axis=1)], axis=1)


def ray_triangle_batch(origins: np.ndarray, dirs: np.ndarray,
                       v0: np.ndarray, edge1: np.ndarray, edge2: np.ndarray
                       ) -> Tuple[np.ndarray, np.ndarray]:
    """Möller-Trumbore: each ray vs each triangle in the batch.

    Args:
        origins: (R, 3)
        dirs:    (R, 3)
        v0:      (T, 3) triangle vertex 0
        edge1:   (T, 3) = v1 - v0
        edge2:   (T, 3) = v2 - v0

    Returns:
        t_hit:  (R,) — nearest hit distance per ray; INF if miss
        f_idx:  (R,) — index of winning triangle in the batch; -1 if miss
    """
    R, T = len(origins), len(v0)
    if R == 0 or T == 0:
        return np.full(R, INF), np.full(R, -1, dtype=np.int64)

    # h = dirs × edge2 → (R, T, 3)
    h = np.cross(dirs[:, None, :], edge2[None, :, :])
    a = np.einsum("tk,rtk->rt", edge1, h)  # (R, T)
    parallel = np.abs(a) < EPS
    a_safe = np.where(parallel, 1.0, a)
    f = 1.0 / a_safe

    s = origins[:, None, :] - v0[None, :, :]            # (R, T, 3)
    u = f * np.einsum("rtk,rtk->rt", s, h)              # (R, T)

    q = np.cross(s, edge1[None, :, :])                   # (R, T, 3)
    v_bary = f * np.einsum("rk,rtk->rt", dirs, q)        # (R, T)

    t = f * np.einsum("tk,rtk->rt", edge2, q)            # (R, T)

    valid = (~parallel) & (u >= 0) & (u <= 1) & \
            (v_bary >= 0) & (u + v_bary <= 1) & (t > EPS)
    t = np.where(valid, t, INF)
    best_f = np.argmin(t, axis=1)
    best_t = t[np.arange(R), best_f]
    hit = best_t < INF
    return np.where(hit, best_t, INF), np.where(hit, best_f, -1)


# ──────────────────────────────────────────────────────────
# BVH (axis-aligned bounding volume hierarchy)
# ──────────────────────────────────────────────────────────
@dataclass
class BVHNode:
    aabb_min: np.ndarray
    aabb_max: np.ndarray
    left: object = None       # BVHNode
    right: object = None      # BVHNode
    item_indices: np.ndarray = None  # leaf only: indices into source array

    @property
    def is_leaf(self) -> bool:
        return self.item_indices is not None


def build_bvh(aabbs: np.ndarray, max_leaf: int = 4) -> BVHNode:
    """Build a BVH over a set of AABBs using simple median-split on the
    longest axis. Returns the root node.

    Args:
        aabbs: (N, 2, 3) — aabbs[i,0]=min, aabbs[i,1]=max
        max_leaf: max items per leaf
    """
    N = len(aabbs)
    if N == 0:
        return BVHNode(aabb_min=np.zeros(3), aabb_max=np.zeros(3),
                       item_indices=np.array([], dtype=np.int64))
    indices = np.arange(N)

    def _recurse(idx):
        if len(idx) <= max_leaf:
            mn = aabbs[idx, 0].min(axis=0)
            mx = aabbs[idx, 1].max(axis=0)
            return BVHNode(aabb_min=mn, aabb_max=mx,
                           item_indices=idx.astype(np.int64))
        # Split along longest axis at the median of centroids
        centers = (aabbs[idx, 0] + aabbs[idx, 1]) / 2
        extents = aabbs[idx, 1].max(axis=0) - aabbs[idx, 0].min(axis=0)
        axis = int(np.argmax(extents))
        order = np.argsort(centers[:, axis])
        idx_sorted = idx[order]
        mid = len(idx_sorted) // 2
        left = _recurse(idx_sorted[:mid])
        right = _recurse(idx_sorted[mid:])
        mn = np.minimum(left.aabb_min, right.aabb_min)
        mx = np.maximum(left.aabb_max, right.aabb_max)
        return BVHNode(aabb_min=mn, aabb_max=mx, left=left, right=right)

    return _recurse(indices)


def _bvh_aabb_test_batch(node: BVHNode, origins: np.ndarray, dirs: np.ndarray,
                         current_best_t: np.ndarray) -> np.ndarray:
    """Return a boolean mask: which rays could still hit this node's AABB
    before their current best_t. Uses >= for tangent-ray acceptance so that
    zero-extent AABBs (e.g. coplanar triangles) don't get falsely rejected.
    """
    if len(origins) == 0:
        return np.array([], dtype=bool)
    inv = _safe_inverse(dirs)
    t1 = (node.aabb_min - origins) * inv
    t2 = (node.aabb_max - origins) * inv
    t_near = np.minimum(t1, t2).max(axis=1)
    t_far = np.maximum(t1, t2).min(axis=1)
    return (t_far >= t_near) & (t_far > EPS) & (t_near < current_best_t)


# ──────────────────────────────────────────────────────────
# SCENE CONTAINER + UNIFIED CAST
# ──────────────────────────────────────────────────────────
@dataclass
class Scene:
    """Container for primitives + meshes + cached top-level BVH."""
    primitives: List[Primitive] = field(default_factory=list)
    meshes: List[Mesh] = field(default_factory=list)
    _bvh: BVHNode = None  # built lazily; items 0..N_prims-1 are primitives,
                          # items N_prims..N_prims+N_meshes-1 are meshes

    def build_bvh(self):
        """Build the top-level BVH over all primitives + meshes."""
        all_aabbs = []
        for p in self.primitives:
            all_aabbs.append(_primitive_aabb(p))
        for m in self.meshes:
            all_aabbs.append(np.stack([m.aabb_min, m.aabb_max]))
        if not all_aabbs:
            self._bvh = build_bvh(np.zeros((0, 2, 3)))
            return
        aabbs = np.stack(all_aabbs)
        self._bvh = build_bvh(aabbs)

    @property
    def bvh(self):
        if self._bvh is None:
            self.build_bvh()
        return self._bvh

    @property
    def n_primitives(self):
        return len(self.primitives)


def _primitive_aabb(p: Primitive) -> np.ndarray:
    """World-space AABB for a primitive. Uses the primitive's bounding sphere
    (max half-extent) as a conservative bound; tight for axis-aligned shapes.
    """
    # Conservative bound: use the max half-extent as a sphere radius
    if p.shape == "sphere":
        r = float(p.half_extents[0])
        return np.stack([p.center - r, p.center + r])
    elif p.shape == "cylinder":
        r = float(p.half_extents[0])
        h = float(p.half_extents[1])
        # Loose for rotated cylinders; tight for axis-aligned
        bound = max(r, h)
        return np.stack([p.center - bound, p.center + bound])
    else:  # box — use diagonal as conservative bound
        bound = float(np.linalg.norm(p.half_extents))
        return np.stack([p.center - bound, p.center + bound])


def _cast_primitive(origins, dirs, prim, ray_indices,
                    best_t, best_color, best_normal, best_pid):
    """Test a subset of rays against one primitive; update best_* in place."""
    if len(ray_indices) == 0:
        return
    o = origins[ray_indices]
    d = dirs[ray_indices]
    if prim.shape == "sphere":
        t, normal = ray_sphere(o, d, prim.center, prim.half_extents[0])
    else:
        o_local = (o - prim.center) @ prim.rotation_matrix.T
        d_local = d @ prim.rotation_matrix.T
        if prim.shape == "box":
            t, n_local = ray_box_local(o_local, d_local, prim.half_extents)
        elif prim.shape == "cylinder":
            t, n_local = ray_cylinder_local(
                o_local, d_local,
                r=float(prim.half_extents[0]),
                half_h=float(prim.half_extents[1]),
            )
        else:
            return
        normal = n_local @ prim.inv_rotation_matrix.T
    color = np.array(prim.color)
    closer = t < best_t[ray_indices]
    upd_idx = ray_indices[closer]
    best_t[upd_idx] = t[closer]
    best_color[upd_idx] = color
    best_normal[upd_idx] = normal[closer]
    best_pid[upd_idx] = prim.piece_id


def _cast_mesh(origins, dirs, mesh, ray_indices,
               best_t, best_color, best_normal, best_pid):
    """Test a subset of rays against a mesh (via the mesh's internal BVH)."""
    if len(ray_indices) == 0:
        return
    # Build mesh BVH lazily over triangles
    if mesh._bvh is None:
        tri_aabbs = _triangle_aabbs(mesh.vertices, mesh.faces)
        mesh._bvh = build_bvh(tri_aabbs, max_leaf=8)

    v0 = mesh.vertices[mesh.faces[:, 0]]
    v1 = mesh.vertices[mesh.faces[:, 1]]
    v2 = mesh.vertices[mesh.faces[:, 2]]
    edge1 = v1 - v0
    edge2 = v2 - v0
    color = np.array(mesh.color)

    def _walk(node, ray_idx):
        if len(ray_idx) == 0:
            return
        mask = _bvh_aabb_test_batch(node, origins[ray_idx], dirs[ray_idx], best_t[ray_idx])
        sur = ray_idx[mask]
        if len(sur) == 0:
            return
        if node.is_leaf:
            fi = node.item_indices
            t_hit, f_hit = ray_triangle_batch(
                origins[sur], dirs[sur], v0[fi], edge1[fi], edge2[fi]
            )
            closer = t_hit < best_t[sur]
            upd = sur[closer]
            best_t[upd] = t_hit[closer]
            best_color[upd] = color
            # Map local face index back to global face index
            winning_global = fi[f_hit[closer]]
            best_normal[upd] = mesh.face_normals[winning_global]
            best_pid[upd] = mesh.piece_id
        else:
            _walk(node.left, sur)
            _walk(node.right, sur)

    _walk(mesh._bvh, ray_indices)


def cast_rays_scene(origins: np.ndarray, dirs: np.ndarray, scene: Scene):
    """BVH-accelerated ray cast against a Scene (primitives + meshes)."""
    N = len(origins)
    best_t = np.full(N, INF)
    best_color = np.zeros((N, 3))
    best_normal = np.zeros((N, 3))
    best_pid = np.full(N, -1, dtype=np.int64)

    if N == 0 or (scene.n_primitives == 0 and len(scene.meshes) == 0):
        return best_t, best_color, best_normal, best_pid

    n_prims = scene.n_primitives

    def _walk(node, ray_idx):
        if len(ray_idx) == 0:
            return
        mask = _bvh_aabb_test_batch(node, origins[ray_idx], dirs[ray_idx], best_t[ray_idx])
        sur = ray_idx[mask]
        if len(sur) == 0:
            return
        if node.is_leaf:
            for item_idx in node.item_indices:
                if item_idx < n_prims:
                    _cast_primitive(origins, dirs, scene.primitives[item_idx], sur,
                                    best_t, best_color, best_normal, best_pid)
                else:
                    mesh = scene.meshes[item_idx - n_prims]
                    _cast_mesh(origins, dirs, mesh, sur,
                               best_t, best_color, best_normal, best_pid)
        else:
            _walk(node.left, sur)
            _walk(node.right, sur)

    _walk(scene.bvh, np.arange(N))
    return best_t, best_color, best_normal, best_pid


# ──────────────────────────────────────────────────────────
# STL LOADER (binary + ASCII)
# ──────────────────────────────────────────────────────────
def load_stl(path: str, color=(0.7, 0.7, 0.7), piece_id: int = 1000) -> Mesh:
    """Load an STL file (binary or ASCII) as a Mesh.

    Auto-detects format by looking at the file header AND scanning for the
    'facet normal' landmark (which appears in ASCII STLs but is unlikely
    as a coincidence in binary data).
    """
    with open(path, "rb") as f:
        all_bytes = f.read()
    is_ascii = (all_bytes.lstrip().startswith(b"solid")
                and b"facet normal" in all_bytes[:10000])
    if is_ascii:
        return _load_stl_ascii(all_bytes, color, piece_id)
    # Binary: skip the 80-byte header
    return _load_stl_binary(all_bytes[80:], color, piece_id)


def _load_stl_binary(buf: bytes, color, piece_id) -> Mesh:
    n_tri = struct.unpack("<I", buf[:4])[0]
    verts = np.zeros((n_tri * 3, 3), dtype=np.float64)
    faces = np.arange(n_tri * 3, dtype=np.int64).reshape(n_tri, 3)
    off = 4
    for i in range(n_tri):
        # Per-triangle layout: 12 bytes normal + 36 bytes (3 vertices × 3 floats)
        # + 2 bytes attribute count = 50 bytes. Read just the 9 vertex floats.
        v = struct.unpack("<9f", buf[off + 12 : off + 48])
        verts[i * 3]     = v[0:3]
        verts[i * 3 + 1] = v[3:6]
        verts[i * 3 + 2] = v[6:9]
        off += 50
    return Mesh(vertices=verts, faces=faces, color=color, piece_id=piece_id)


def _load_stl_ascii(buf: bytes, color, piece_id) -> Mesh:
    text = buf.decode("utf-8", errors="replace")
    verts = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("vertex "):
            parts = line.split()
            verts.append([float(parts[1]), float(parts[2]), float(parts[3])])
    verts = np.array(verts, dtype=np.float64)
    n_tri = len(verts) // 3
    faces = np.arange(n_tri * 3, dtype=np.int64).reshape(n_tri, 3)
    return Mesh(vertices=verts[:n_tri * 3], faces=faces, color=color, piece_id=piece_id)


# ──────────────────────────────────────────────────────────
# FRUSTUM CULLING (pinhole only)
# ──────────────────────────────────────────────────────────
def pinhole_frustum_planes(cam, near: float = 0.05, far: float = 1000.0) -> np.ndarray:
    """Return 6 plane equations (a, b, c, d) such that a point is INSIDE the
    frustum iff a·x + b·y + c·z + d ≤ 0 for all 6 planes (inward-normal form).

    Only meaningful for pinhole/telephoto cameras with finite FOV.
    """
    forward = cam.target - cam.position
    forward = forward / np.linalg.norm(forward)
    right = np.cross(forward, cam.up)
    rn = np.linalg.norm(right)
    if rn < EPS:
        alt = np.array([0., 0., 1.]) if abs(cam.up[2]) < 0.99 else np.array([1., 0., 0.])
        right = np.cross(forward, alt)
        right = right / np.linalg.norm(right)
    else:
        right = right / rn
    up = np.cross(right, forward)
    aspect = cam.width / cam.height
    half_v = math.tan(math.radians(cam.fov_deg) / 2)
    half_h = half_v * aspect
    pos = cam.position
    # 6 planes: near, far, left, right, top, bottom (inward normals)
    planes = []
    # Near plane: outward normal = -forward, so inward = +forward;
    # point on near plane = pos + near*forward
    near_pt = pos + near * forward
    n_in = -forward
    planes.append(np.append(n_in, -n_in @ near_pt))
    far_pt = pos + far * forward
    n_in = forward
    planes.append(np.append(n_in, -n_in @ far_pt))
    # Side planes — normals point inward toward the frustum interior
    left_n = -(forward * half_h + right) / math.sqrt(1 + half_h * half_h)
    right_n = -(forward * half_h - right) / math.sqrt(1 + half_h * half_h)
    top_n = -(forward * half_v - up) / math.sqrt(1 + half_v * half_v)
    bot_n = -(forward * half_v + up) / math.sqrt(1 + half_v * half_v)
    for n in (left_n, right_n, top_n, bot_n):
        planes.append(np.append(n, -n @ pos))
    return np.stack(planes)


def aabb_outside_frustum(aabb_min, aabb_max, planes) -> bool:
    """True if the AABB is entirely on the outside (positive) side of ANY
    frustum plane. Conservative — may keep some AABBs that aren't visible,
    but won't reject any that are."""
    # For each plane, find the corner of the AABB farthest in the inward
    # direction. If even that corner is on the outside, the AABB is outside.
    for p in planes:
        n = p[:3]; d = p[3]
        # Choose corner maximizing -(n·v + d)
        corner = np.where(n > 0, aabb_min, aabb_max)
        if n @ corner + d > 0:
            return True
    return False


def cull_scene_to_frustum(scene: Scene, planes: np.ndarray) -> Scene:
    """Return a new Scene containing only items whose AABBs aren't entirely
    outside the frustum. The pruned scene gets a fresh BVH on first cast."""
    if planes is None or len(planes) == 0:
        return scene
    pruned = Scene()
    for p in scene.primitives:
        ab = _primitive_aabb(p)
        if not aabb_outside_frustum(ab[0], ab[1], planes):
            pruned.primitives.append(p)
    for m in scene.meshes:
        if not aabb_outside_frustum(m.aabb_min, m.aabb_max, planes):
            pruned.meshes.append(m)
    return pruned


# ──────────────────────────────────────────────────────────
# BACKWARDS-COMPATIBLE cast_rays
# ──────────────────────────────────────────────────────────
_legacy_cast_rays = cast_rays  # save the original linear-scan implementation


def cast_rays(origins, dirs, scene_or_prims):
    """Cast rays against a Scene (BVH-accelerated) or a list of Primitives
    (legacy linear scan; for big scenes wrap in Scene() for BVH speedup).
    """
    if isinstance(scene_or_prims, Scene):
        return cast_rays_scene(origins, dirs, scene_or_prims)
    if isinstance(scene_or_prims, list):
        # Auto-wrap into a Scene only if it's worth it (≥8 primitives).
        # Smaller scenes are faster without BVH overhead.
        if len(scene_or_prims) >= 8:
            scene = Scene(primitives=list(scene_or_prims))
            return cast_rays_scene(origins, dirs, scene)
        return _legacy_cast_rays(origins, dirs, scene_or_prims)
    raise TypeError(f"cast_rays expects Scene or list of Primitive, got {type(scene_or_prims)}")


# ── LENS EXTENSION (merged from lenses.py) ──────────────────────────────



def _basis(cam: Camera):
    forward = cam.target - cam.position
    forward = forward / np.linalg.norm(forward)
    right = np.cross(forward, cam.up)
    rn = np.linalg.norm(right)
    if rn < EPS:
        # Gimbal-lock fallback for cameras pointing along the up axis
        alt = np.array([0., 0., 1.]) if abs(cam.up[2]) < 0.99 else np.array([1., 0., 0.])
        right = np.cross(forward, alt)
        right = right / np.linalg.norm(right)
    else:
        right = right / rn
    up = np.cross(right, forward)
    return forward, right, up


def _stratified_pixels(W: int, H: int, n_samples: int, rng) -> Tuple[np.ndarray, np.ndarray]:
    """Shared stratified pixel sampler. Returns (px, py)."""
    aspect = W / H
    grid_w = max(1, int(math.sqrt(n_samples * aspect)))
    grid_h = max(1, n_samples // grid_w)
    gx, gy = np.meshgrid(np.arange(grid_w), np.arange(grid_h))
    jx = rng.random(gx.shape); jy = rng.random(gy.shape)
    px = ((gx + jx) / grid_w * W).flatten()
    py = ((gy + jy) / grid_h * H).flatten()
    return px, py


# ──────────────────────────────────────────────────────────
# LENS: PINHOLE (the original)
# ──────────────────────────────────────────────────────────
def rays_pinhole(cam: Camera, n_samples: int, rng) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    W, H = cam.width, cam.height
    aspect = W / H
    fov_rad = math.radians(cam.fov_deg)
    half_h = math.tan(fov_rad / 2)
    half_w = half_h * aspect
    px, py = _stratified_pixels(W, H, n_samples, rng)
    ndc_x = (px / W - 0.5) * 2 * half_w
    ndc_y = (0.5 - py / H) * 2 * half_h
    forward, right, up = _basis(cam)
    dirs = (forward[None, :]
            + ndc_x[:, None] * right[None, :]
            + ndc_y[:, None] * up[None, :])
    dirs = dirs / np.linalg.norm(dirs, axis=1, keepdims=True)
    origins = np.tile(cam.position[None, :], (len(dirs), 1))
    return origins, dirs, np.stack([px, py], axis=1)


# ──────────────────────────────────────────────────────────
# LENS: FISHEYE (equidistant projection)
# ──────────────────────────────────────────────────────────
def rays_fisheye(cam: Camera, n_samples: int, rng) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Equidistant fisheye. r_image = f · θ, so angle from optical axis is
    linear in image radius. 180° gives a hemisphere in one frame."""
    W, H = cam.width, cam.height
    max_theta = math.radians(cam.fisheye_fov_deg / 2)
    px, py = _stratified_pixels(W, H, n_samples, rng)

    # NDC, then make it a square in the smaller dimension so the fisheye
    # circle fits inside the image
    if W >= H:
        ndc_x = (px / W - 0.5) * 2 * (W / H)
        ndc_y = (0.5 - py / H) * 2
    else:
        ndc_x = (px / W - 0.5) * 2
        ndc_y = (0.5 - py / H) * 2 * (H / W)

    r = np.sqrt(ndc_x*ndc_x + ndc_y*ndc_y)
    inside = r <= 1.0
    ndc_x, ndc_y, r = ndc_x[inside], ndc_y[inside], r[inside]
    px, py = px[inside], py[inside]

    theta = r * max_theta
    phi = np.arctan2(ndc_y, ndc_x)
    forward, right, up = _basis(cam)
    cos_t, sin_t = np.cos(theta), np.sin(theta)
    cos_p, sin_p = np.cos(phi), np.sin(phi)
    dirs = (cos_t[:, None] * forward[None, :]
            + (sin_t * cos_p)[:, None] * right[None, :]
            + (sin_t * sin_p)[:, None] * up[None, :])
    dirs = dirs / np.linalg.norm(dirs, axis=1, keepdims=True)
    origins = np.tile(cam.position[None, :], (len(dirs), 1))
    return origins, dirs, np.stack([px, py], axis=1)


# ──────────────────────────────────────────────────────────
# LENS: ORTHOGRAPHIC (parallel rays)
# ──────────────────────────────────────────────────────────
def rays_orthographic(cam: Camera, n_samples: int, rng) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Parallel rays. ortho_size is the half-width of the view frame in
    world units. Useful for floor plans (top-down) and elevations (side)."""
    W, H = cam.width, cam.height
    aspect = W / H
    half_w = cam.ortho_size
    half_h = cam.ortho_size / aspect
    px, py = _stratified_pixels(W, H, n_samples, rng)
    ndc_x = (px / W - 0.5) * 2 * half_w
    ndc_y = (0.5 - py / H) * 2 * half_h
    forward, right, up = _basis(cam)
    n_rays = len(px)
    dirs = np.tile(forward[None, :], (n_rays, 1))
    origins = (cam.position[None, :]
               + ndc_x[:, None] * right[None, :]
               + ndc_y[:, None] * up[None, :])
    return origins, dirs, np.stack([px, py], axis=1)


# ──────────────────────────────────────────────────────────
# LENS: EQUIRECTANGULAR (360°×180° spherical)
# ──────────────────────────────────────────────────────────
def rays_equirectangular(cam: Camera, n_samples: int, rng) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Full sphere projection. X axis = longitude [-π, π], Y axis =
    latitude [-π/2, π/2]. The 'forward' direction is at the image center."""
    W, H = cam.width, cam.height
    px, py = _stratified_pixels(W, H, n_samples, rng)
    lon = (px / W - 0.5) * 2 * math.pi
    lat = (0.5 - py / H) * math.pi

    forward, right, up = _basis(cam)
    cos_lat = np.cos(lat); sin_lat = np.sin(lat)
    cos_lon = np.cos(lon); sin_lon = np.sin(lon)
    dirs = (cos_lat[:, None] * (cos_lon[:, None] * forward[None, :]
                                + sin_lon[:, None] * right[None, :])
            + sin_lat[:, None] * up[None, :])
    dirs = dirs / np.linalg.norm(dirs, axis=1, keepdims=True)
    origins = np.tile(cam.position[None, :], (len(dirs), 1))
    return origins, dirs, np.stack([px, py], axis=1)


# ──────────────────────────────────────────────────────────
# REGISTRY + DISPATCH
# ──────────────────────────────────────────────────────────
LENS_REGISTRY = {
    "pinhole":         rays_pinhole,
    "telephoto":       rays_pinhole,   # alias: pinhole with narrow fov_deg
    "fisheye":         rays_fisheye,
    "orthographic":    rays_orthographic,
    "equirectangular": rays_equirectangular,
}


def fire_burst(cam: Camera, prims: List[Primitive], n_samples: int, seed: int) -> Burst:
    """Fire a burst using the camera's lens type."""
    rng = np.random.default_rng(seed)
    gen = LENS_REGISTRY.get(cam.lens, rays_pinhole)
    origins, dirs, pixels = gen(cam, n_samples, rng)
    t, color, normal, pid = cast_rays(origins, dirs, prims)
    hit = t < INF
    coverage = float(hit.mean()) if len(t) else 0.0
    unique_pieces = int(len(np.unique(pid[hit]))) if hit.any() else 0
    return Burst(
        cam=cam, pixels=pixels, origins=origins, dirs=dirs, depths=t, colors=color,
        normals=normal, piece_ids=pid,
        coverage=coverage, unique_pieces=unique_pieces,
    )


# ──────────────────────────────────────────────────────────
# CUBEMAP HELPER (6 perpendicular pinholes from one point)
# ──────────────────────────────────────────────────────────
def cubemap_cameras(position, width: int = 400, height: int = 400) -> List[Tuple[str, Camera]]:
    """Return 6 cameras forming a cubemap rig at `position`.
    Each is a 90° FOV pinhole pointing at one face of the cube."""
    p = np.asarray(position, dtype=float)
    face_specs = [
        ("+X", [ 1,  0,  0], [0, 1, 0]),
        ("-X", [-1,  0,  0], [0, 1, 0]),
        ("+Y", [ 0,  1,  0], [0, 0, 1]),
        ("-Y", [ 0, -1,  0], [0, 0,-1]),
        ("+Z", [ 0,  0,  1], [0, 1, 0]),
        ("-Z", [ 0,  0, -1], [0, 1, 0]),
    ]
    cams = []
    for name, d, up in face_specs:
        d = np.array(d, float); up = np.array(up, float)
        cams.append((name, Camera(
            position=p.copy(),
            target=p + d,
            up=up,
            fov_deg=90.0,
            width=width, height=height,
            lens="pinhole",
        )))
    return cams


# ──────────────────────────────────────────────────────────
# LENS-AWARE PROJECTION (inverse of each ray generator)
# ──────────────────────────────────────────────────────────
def _project_pinhole(points: np.ndarray, cam: Camera):
    """Inverse of rays_pinhole: world point → (sx, sy, depth, in_bounds)."""
    forward, right, up = _basis(cam)
    W, H = cam.width, cam.height
    aspect = W / H
    fov_rad = math.radians(cam.fov_deg)
    half_h = math.tan(fov_rad / 2)
    half_w = half_h * aspect

    rel = points - cam.position
    depth = rel @ forward
    in_front = depth > 0.05
    x_cam = rel @ right
    y_cam = rel @ up

    sx = np.full(len(points), -1.0)
    sy = np.full(len(points), -1.0)
    safe_d = np.where(in_front, depth, 1.0)
    sx[in_front] = (0.5 + x_cam[in_front] / (safe_d[in_front] * 2 * half_w)) * W
    sy[in_front] = (0.5 - y_cam[in_front] / (safe_d[in_front] * 2 * half_h)) * H
    in_bounds = in_front & (sx >= 0) & (sx < W) & (sy >= 0) & (sy < H)
    return sx, sy, depth, in_bounds


def _project_fisheye(points: np.ndarray, cam: Camera):
    """Inverse of rays_fisheye (equidistant projection)."""
    forward, right, up = _basis(cam)
    W, H = cam.width, cam.height
    max_theta = math.radians(cam.fisheye_fov_deg / 2)

    rel = points - cam.position
    dist = np.linalg.norm(rel, axis=1).clip(EPS)
    dirs_unit = rel / dist[:, None]

    cos_theta = (dirs_unit @ forward).clip(-1, 1)
    theta = np.arccos(cos_theta)
    in_view = theta <= max_theta

    x_proj = dirs_unit @ right
    y_proj = dirs_unit @ up
    phi = np.arctan2(y_proj, x_proj)

    r = theta / max_theta
    ndc_x = r * np.cos(phi)
    ndc_y = r * np.sin(phi)

    # Inverse of rays_fisheye NDC scaling
    if W >= H:
        sx = ((ndc_x / (W / H)) * 0.5 + 0.5) * W
        sy = (-ndc_y * 0.5 + 0.5) * H
    else:
        sx = (ndc_x * 0.5 + 0.5) * W
        sy = ((-ndc_y / (H / W)) * 0.5 + 0.5) * H

    in_bounds = in_view & (sx >= 0) & (sx < W) & (sy >= 0) & (sy < H)
    return sx, sy, dist, in_bounds


def _project_orthographic(points: np.ndarray, cam: Camera):
    """Inverse of rays_orthographic. Depth = along-forward distance."""
    forward, right, up = _basis(cam)
    W, H = cam.width, cam.height
    aspect = W / H
    half_w = cam.ortho_size
    half_h = cam.ortho_size / aspect

    rel = points - cam.position
    depth = rel @ forward
    x_cam = rel @ right
    y_cam = rel @ up

    sx = (x_cam / (2 * half_w) + 0.5) * W
    sy = (-y_cam / (2 * half_h) + 0.5) * H

    in_bounds = (depth > 0.05) & (sx >= 0) & (sx < W) & (sy >= 0) & (sy < H)
    return sx, sy, depth, in_bounds


def _project_equirectangular(points: np.ndarray, cam: Camera):
    """Inverse of rays_equirectangular. Depth = distance from camera."""
    forward, right, up = _basis(cam)
    W, H = cam.width, cam.height

    rel = points - cam.position
    dist = np.linalg.norm(rel, axis=1).clip(EPS)
    dirs_unit = rel / dist[:, None]

    sin_lat = (dirs_unit @ up).clip(-1, 1)
    lat = np.arcsin(sin_lat)
    fwd_comp = dirs_unit @ forward
    rt_comp = dirs_unit @ right
    lon = np.arctan2(rt_comp, fwd_comp)

    sx = (lon / math.pi * 0.5 + 0.5) * W
    sy = (-lat / (math.pi / 2) * 0.5 + 0.5) * H

    in_bounds = (sx >= 0) & (sx < W) & (sy >= 0) & (sy < H)
    return sx, sy, dist, in_bounds


LENS_PROJECTORS = {
    "pinhole":         _project_pinhole,
    "telephoto":       _project_pinhole,
    "fisheye":         _project_fisheye,
    "orthographic":    _project_orthographic,
    "equirectangular": _project_equirectangular,
}


def project_to_camera(points: np.ndarray, cam: Camera):
    """Lens-aware world→pixel projection. Dispatches on cam.lens."""
    projector = LENS_PROJECTORS.get(cam.lens, _project_pinhole)
    return projector(points, cam)


# ──────────────────────────────────────────────────────────
# LENS-AWARE FUSION
# ──────────────────────────────────────────────────────────
def fuse_bursts_pointcloud(bursts, canonical_cam: Camera, mode: str = "shaded",
                           dot_size: int = 1, bg: str = "#08101a"):
    """Multi-view fusion: aggregate hits as world point cloud, project through
    canonical_cam (any lens). Back-to-front splat."""
    all_pts, all_cols, all_norms = [], [], []
    for b in bursts:
        pts, cols, norms, _, _ = _burst_world_points(b)
        if len(pts):
            all_pts.append(pts); all_cols.append(cols); all_norms.append(norms)
    if not all_pts:
        return Image.new("RGB", (canonical_cam.width, canonical_cam.height), bg)
    pts = np.vstack(all_pts); cols = np.vstack(all_cols); norms = np.vstack(all_norms)

    sx, sy, depth, ok = project_to_camera(pts, canonical_cam)
    sx, sy = sx[ok].astype(int), sy[ok].astype(int)
    cols, norms, depth = cols[ok], norms[ok], depth[ok]

    order = np.argsort(-depth)
    sx, sy, cols, norms = sx[order], sy[order], cols[order], norms[order]

    if mode == "shaded":
        light = np.array([0.4, 0.7, 0.3]); light /= np.linalg.norm(light)
        ndotl = np.clip((norms * light).sum(axis=1), 0.3, 1.0)
        out_col = cols * ndotl[:, None]
    elif mode == "lidar":
        out_col = depth_to_color(depth[order], 0.5, 20.0)
    else:
        out_col = cols

    W, H = canonical_cam.width, canonical_cam.height
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)
    out_col_int = (np.clip(out_col, 0, 1) * 255).astype(np.uint8)
    for i in range(len(sx)):
        c = tuple(int(v) for v in out_col_int[i])
        x, y = int(sx[i]), int(sy[i])
        if dot_size == 1:
            img.putpixel((x, y), c)
        else:
            draw.ellipse([x-dot_size, y-dot_size, x+dot_size, y+dot_size], fill=c)
    return img


def fuse_bursts_attention(bursts, canonical_cam: Camera,
                          depth_bin: float = 0.30,
                          confidence_threshold: float = 0.15,
                          tile: int = 2,
                          alpha_gain: float = 1.5,
                          smooth_heatmap: bool = False,
                          bg_rgb: tuple = (8, 16, 26)
                          ) -> tuple:
    """Lens-aware attention-weighted fusion. Returns (color, heatmap).
    The canonical_cam can use any lens — projection dispatches on cam.lens."""
    tile = max(1, int(tile))
    depth_bin = max(float(depth_bin), EPS)
    alpha_gain = max(float(alpha_gain), EPS)
    confidence_threshold = max(float(confidence_threshold), 0.0)

    W, H = canonical_cam.width, canonical_cam.height

    all_pts, all_cols, all_weights = [], [], []
    for b in bursts:
        pts, cols, norms, depths_b, hit_idx = _burst_world_points(b)
        if not len(pts):
            continue
        source_dirs = b.dirs[hit_idx]
        align = np.abs((norms * -source_dirs).sum(axis=1)).clip(0.1, 1.0)
        depth_w = 1.0 / (1.0 + 0.05 * depths_b)
        pilot_w = max(0.1, b.pilot_score)
        weights = align * depth_w * pilot_w

        light = np.array([0.4, 0.7, 0.3]); light /= np.linalg.norm(light)
        ndotl = np.clip((norms * light).sum(axis=1), 0.3, 1.0)
        shaded = cols * ndotl[:, None]

        all_pts.append(pts); all_cols.append(shaded)
        all_weights.append(weights)

    if not all_pts:
        empty = Image.new("RGB", (W, H), bg_rgb)
        return empty, empty

    pts = np.vstack(all_pts); cols = np.vstack(all_cols)
    weights = np.concatenate(all_weights)

    # Lens-aware projection
    sx, sy, can_depth, ok = project_to_camera(pts, canonical_cam)
    sx_i = sx[ok].astype(int); sy_i = sy[ok].astype(int)
    cols, weights, can_depth = cols[ok], weights[ok], can_depth[ok]
    bucket = (can_depth / depth_bin).astype(int)

    tile_x = sx_i // tile
    tile_y = sy_i // tile

    accum = {}
    for i in range(len(sx_i)):
        key = (int(tile_x[i]), int(tile_y[i]), int(bucket[i]))
        w = weights[i]
        if key in accum:
            acc_c, acc_w, acc_d = accum[key]
            accum[key] = (acc_c + w * cols[i], acc_w + w, min(acc_d, can_depth[i]))
        else:
            accum[key] = (w * cols[i], w, can_depth[i])

    img_arr = np.full((H, W, 3), bg_rgb, dtype=np.float64) / 255.0
    conf_arr = np.zeros((H, W), dtype=np.float64)
    best_depth = {}
    bg_norm = np.array(bg_rgb) / 255.0

    for (tx, ty, _), (sw_c, sw, d) in accum.items():
        if sw < confidence_threshold:
            continue
        if (tx, ty) in best_depth and best_depth[(tx, ty)] <= d:
            continue
        color = sw_c / sw
        alpha = 1.0 - math.exp(-alpha_gain * sw)
        blended = color * alpha + bg_norm * (1.0 - alpha)
        x0, y0 = tx * tile, ty * tile
        x1, y1 = min(x0 + tile, W), min(y0 + tile, H)
        if 0 <= x0 < W and 0 <= y0 < H:
            img_arr[y0:y1, x0:x1] = blended
            conf_arr[y0:y1, x0:x1] = sw
            best_depth[(tx, ty)] = d

    color_img = Image.fromarray((np.clip(img_arr, 0, 1) * 255).astype(np.uint8))
    heat_img = _confidence_heatmap(conf_arr, bg_rgb=bg_rgb, smooth=smooth_heatmap)
    return color_img, heat_img


# ──────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────
def scene_radius(prims) -> float:
    """Return a radius bounding all primitives (centers + extents) with 10% margin.
    Useful for auto-picking ortho_size so content doesn't silently clip.

    Note: uses the maximum half-extent of each primitive as a conservative
    bound. Exact for axis-aligned shapes; slightly loose for rotated boxes.
    """
    if not prims:
        return 1.0
    lows = np.array([p.center - p.half_extents.max() for p in prims])
    highs = np.array([p.center + p.half_extents.max() for p in prims])
    bb_min = lows.min(axis=0)
    bb_max = highs.max(axis=0)
    diag = np.linalg.norm(bb_max - bb_min)
    return float(diag / 2 * 1.1)

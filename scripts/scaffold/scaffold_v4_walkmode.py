#!/usr/bin/env python3
"""
scaffold.py — Generate a self-contained Three.js HTML scaffold.

Outputs a ready-to-run HTML file with:
  - Three.js r170 via ES module importmap (single file, no build step)
  - Real OrbitControls (touch, keyboard, damping, distance limits)
  - Configurable camera, grid, axes
  - Ambient + directional + fill lighting
  - A PARAMS object placeholder
  - A buildModel() stub

Usage:
    python scaffold.py                          # stdout
    python scaffold.py --out model.html         # write to file
    python scaffold.py --title "Clock Tower"    # custom title
    python scaffold.py --camera-y 10 --camera-z 20
    python scaffold.py --no-grid --no-axes
    python scaffold.py --bg "#1a1a2e"
"""

import argparse
import sys


def generate_scaffold(
    title: str = "3D Model",
    camera_pos: tuple[float, float, float] = (10, 10, 20),
    bg_color: str = "#1a1a2e",
    show_grid: bool = True,
    show_axes: bool = True,
    grid_size: int = 40,
    grid_divisions: int = 40,
    params_block: str = "",
    build_body: str = "",
) -> str:

    params_js = params_block or """\
    // ── Central parameters ──────────────────────────────────
    // Edit these, everything else derives from them.
    const PARAMS = {
        // overall
        unit: 'm',
        groundY: 0,

        // example part
        baseWidth: 4,
        baseDepth: 3,
        baseHeight: 0.5,
    };"""

    build_js = build_body or """\
    function buildModel(scene) {
        const g = new THREE.Group();

        // ── Example: ground slab ──
        const baseGeo = new THREE.BoxGeometry(
            PARAMS.baseWidth, PARAMS.baseHeight, PARAMS.baseDepth
        );
        const baseMat = new THREE.MeshStandardMaterial({ color: 0xcccccc });
        const base = new THREE.Mesh(baseGeo, baseMat);
        base.position.y = PARAMS.groundY + PARAMS.baseHeight / 2;
        base.castShadow = true;
        base.receiveShadow = true;
        g.add(base);

        // ── Add more parts here ──

        scene.add(g);
        return g;
    }"""

    grid_js = f"""
        const gridHelper = new THREE.GridHelper({grid_size}, {grid_divisions}, 0x444444, 0x222222);
        scene.add(gridHelper);""" if show_grid else ""

    axes_js = """
        const axesHelper = new THREE.AxesHelper(8);
        scene.add(axesHelper);""" if show_axes else ""

    cx, cy, cz = camera_pos

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{title}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ overflow: hidden; background: {bg_color}; }}
  canvas {{ display: block; }}
  #info {{
    position: fixed; top: 12px; left: 12px;
    color: #aaa; font: 13px/1.4 monospace;
    background: rgba(0,0,0,0.5); padding: 8px 12px;
    border-radius: 6px; pointer-events: none;
    max-width: 320px;
  }}
</style>
</head>
<body>

<div id="info">
  <strong>{title}</strong><br>
  Orbit: drag &middot; Zoom: scroll &middot; Pan: right-drag
</div>

<script type="importmap">
{{
  "imports": {{
    "three": "https://cdn.jsdelivr.net/npm/three@0.170/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.170/examples/jsm/"
  }}
}}
</script>

<script type="module">
    import * as THREE from 'three';
    import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';

    // Make THREE available globally for buildModel compatibility
    window.THREE = THREE;

    // ══════════════════════════════════════════════════════════
    //  PARAMETERS
    // ══════════════════════════════════════════════════════════
{params_js}

    // ══════════════════════════════════════════════════════════
    //  MATERIAL PALETTE
    // ══════════════════════════════════════════════════════════
    const _matCache = {{}};
    function matByName(name) {{
        if (_matCache[name]) return _matCache[name];
        const palette = {{
            stone:      {{ color: 0xc4b8a8, roughness: 0.85, metalness: 0.0 }},
            brick:      {{ color: 0xa0522d, roughness: 0.75, metalness: 0.0 }},
            metal:      {{ color: 0x555555, roughness: 0.45, metalness: 0.8 }},
            metal_pol:  {{ color: 0xcccccc, roughness: 0.15, metalness: 0.95 }},
            wood:       {{ color: 0x5c3a1e, roughness: 0.80, metalness: 0.0 }},
            wood_furn:  {{ color: 0x8b6914, roughness: 0.70, metalness: 0.0 }},
            wood_dark:  {{ color: 0x5c3a1e, roughness: 0.80, metalness: 0.0 }},
            plaster:    {{ color: 0xd4c5a9, roughness: 0.90, metalness: 0.0 }},
            floor:      {{ color: 0x6b4423, roughness: 0.85, metalness: 0.0 }},
            grass:      {{ color: 0x556b2f, roughness: 0.90, metalness: 0.0 }},
            marble:     {{ color: 0xf0ece0, roughness: 0.40, metalness: 0.0 }},
            accent:     {{ color: 0xcc4444, roughness: 0.50, metalness: 0.0 }},
            roof:       {{ color: 0x8b3a3a, roughness: 0.75, metalness: 0.0 }},
            cloth:      {{ color: 0x4444aa, roughness: 0.85, metalness: 0.0 }},
            cloth_dark: {{ color: 0x333355, roughness: 0.85, metalness: 0.0 }},
            skin:       {{ color: 0xddaa88, roughness: 0.70, metalness: 0.0 }},
            leaf:       {{ color: 0x33aa44, roughness: 0.75, metalness: 0.0 }},
        }};
        const props = palette[name];
        let mat;
        if (name === 'glass') {{
            mat = new THREE.MeshPhysicalMaterial({{ color: 0x88bbdd, transmission: 0.9, roughness: 0.05 }});
        }} else if (props) {{
            mat = new THREE.MeshStandardMaterial(props);
        }} else {{
            // Try parsing as hex color string
            if (typeof name === 'string' && name.startsWith('#')) {{
                mat = new THREE.MeshStandardMaterial({{ color: parseInt(name.slice(1), 16), roughness: 0.75 }});
            }} else {{
                mat = new THREE.MeshStandardMaterial({{ color: 0xcccccc, roughness: 0.80, metalness: 0.1 }});
            }}
        }}
        _matCache[name] = mat;
        return mat;
    }}

    // ══════════════════════════════════════════════════════════
    //  BUILD MODEL
    // ══════════════════════════════════════════════════════════
{build_js}

    // ══════════════════════════════════════════════════════════
    //  SCENE SETUP (usually no need to edit below)
    // ══════════════════════════════════════════════════════════
    const scene = new THREE.Scene();
    scene.background = new THREE.Color('{bg_color}');
    scene.fog = new THREE.Fog('{bg_color}', 80, 200);

    const camera = new THREE.PerspectiveCamera(
        50, window.innerWidth / window.innerHeight, 0.1, 500
    );
    camera.position.set({cx}, {cy}, {cz});

    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    document.body.appendChild(renderer.domElement);

    // Lighting
    const ambient = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambient);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(15, 25, 20);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.set(1024, 1024);
    dirLight.shadow.camera.near = 0.5;
    dirLight.shadow.camera.far = 80;
    dirLight.shadow.camera.left = -20;
    dirLight.shadow.camera.right = 20;
    dirLight.shadow.camera.top = 20;
    dirLight.shadow.camera.bottom = -20;
    scene.add(dirLight);

    const fillLight = new THREE.DirectionalLight(0x8899bb, 0.3);
    fillLight.position.set(-10, 8, -10);
    scene.add(fillLight);
{grid_js}
{axes_js}

    // Build
    const model = buildModel(scene);

    // Controls (real OrbitControls with touch, keyboard, damping)
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.target.set(0, {cy * 0.3:.1f}, 0);

    // Render loop
    function animate() {{
        requestAnimationFrame(animate);
        if (window._walkMode) {{ window._walkUpdate(); }} else {{ controls.update(); }}
        renderer.render(scene, camera);
    }}
    animate();

    // ── Walk Mode ──────────────────────────────────────
    (function() {{
        let walkMode = false;
        let wk = {{ x: 0, y: 1.6, z: 0, rotY: 0, rotX: 0 }};
        const keys = {{}};
        const SPEED = 0.1;

        // UI
        const btn = document.createElement('div');
        btn.innerHTML = '🚶 Walk [F]';
        btn.style.cssText = 'position:fixed;bottom:14px;right:14px;color:#fff;background:rgba(0,0,0,0.7);padding:8px 14px;border-radius:6px;cursor:pointer;font:13px/1 monospace;z-index:100;border:1px solid #555;user-select:none;';
        document.body.appendChild(btn);

        const hud = document.createElement('div');
        hud.style.cssText = 'position:fixed;bottom:14px;left:50%;transform:translateX(-50%);color:#aaa;background:rgba(0,0,0,0.6);padding:6px 14px;border-radius:6px;font:11px/1.3 monospace;z-index:100;display:none;white-space:nowrap;';
        document.body.appendChild(hud);

        function toggle() {{
            walkMode = !walkMode;
            window._walkMode = walkMode;
            btn.innerHTML = walkMode ? '🔭 Orbit [F]' : '🚶 Walk [F]';
            btn.style.borderColor = walkMode ? '#4a4' : '#555';
            hud.style.display = walkMode ? 'block' : 'none';
            if (walkMode) {{
                wk = {{ x: camera.position.x, y: 1.6, z: camera.position.z, rotY: 0, rotX: 0 }};
                controls.enabled = false;
                renderer.domElement.requestPointerLock();
            }} else {{
                controls.enabled = true;
                document.exitPointerLock();
                camera.position.set({cx}, {cy}, {cz});
                controls.target.set(0, {cy * 0.3:.1f}, 0);
            }}
        }}

        btn.onclick = toggle;
        document.addEventListener('keydown', e => {{
            keys[e.key.toLowerCase()] = true;
            if (e.key.toLowerCase() === 'f' && e.target === document.body) toggle();
            if (e.key === 'Escape' && walkMode) toggle();
        }});
        document.addEventListener('keyup', e => {{ keys[e.key.toLowerCase()] = false; }});

        // Mouse look
        document.addEventListener('mousemove', e => {{
            if (!walkMode || !document.pointerLockElement) return;
            wk.rotY -= e.movementX * 0.002;
            wk.rotX = Math.max(-1.4, Math.min(1.4, wk.rotX - e.movementY * 0.002));
        }});

        // Re-lock on click
        renderer.domElement.addEventListener('click', () => {{
            if (walkMode && !document.pointerLockElement) renderer.domElement.requestPointerLock();
        }});

        // Q/E rotation (keyboard look without mouse)
        // Arrow keys + WASD movement

        window._walkUpdate = function() {{
            const fwd = {{ x: Math.sin(wk.rotY), z: Math.cos(wk.rotY) }};
            const rgt = {{ x: Math.cos(wk.rotY), z: -Math.sin(wk.rotY) }};

            if (keys['w'] || keys['arrowup'])    {{ wk.x += fwd.x*SPEED; wk.z += fwd.z*SPEED; }}
            if (keys['s'] || keys['arrowdown'])  {{ wk.x -= fwd.x*SPEED; wk.z -= fwd.z*SPEED; }}
            if (keys['a'] || keys['arrowleft'])  {{ wk.x -= rgt.x*SPEED; wk.z -= rgt.z*SPEED; }}
            if (keys['d'] || keys['arrowright']) {{ wk.x += rgt.x*SPEED; wk.z += rgt.z*SPEED; }}
            if (keys['q']) wk.rotY += 0.03;
            if (keys['e']) wk.rotY -= 0.03;
            if (keys['r']) wk.rotX = Math.min(1.4, wk.rotX + 0.02);
            if (keys['t']) wk.rotX = Math.max(-1.4, wk.rotX - 0.02);

            camera.position.set(wk.x, wk.y, wk.z);
            camera.lookAt(
                wk.x + Math.sin(wk.rotY) * 10,
                wk.y + Math.sin(wk.rotX) * 10,
                wk.z + Math.cos(wk.rotY) * 10
            );

            const deg = ((wk.rotY * 180 / Math.PI) % 360 + 360) % 360;
            const dir = ['N','NE','E','SE','S','SW','W','NW'][Math.round(deg/45)%8];
            hud.innerHTML = 'pos: ('+wk.x.toFixed(1)+', '+wk.z.toFixed(1)+') '+
                ' facing: '+dir+
                ' &nbsp;│&nbsp; WASD: move &nbsp; Mouse/QE: look &nbsp; F: orbit &nbsp; Esc: exit';
        }};

        window._walkMode = false;
    }})();

    // Resize
    window.addEventListener('resize', () => {{
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    }});
</script>
</body>
</html>"""


# ── Packet → Three.js code generation ─────────────────────────────────────────

def _hex_to_js_int(color: str) -> str:
    """'#aabbcc' → '0xaabbcc'"""
    return "0x" + color.lstrip("#").lower()


def _geo_js(shape: str, dims: list) -> str:
    """Return a Three.js geometry constructor call for the given shape and dims."""
    if shape == "box":
        w, h, d = dims
        return f"new THREE.BoxGeometry({w}, {h}, {d})"
    if shape == "cylinder":
        rt, rb, h = dims
        return f"new THREE.CylinderGeometry({rt}, {rb}, {h}, 16)"
    if shape == "cone":
        r, h = dims
        return f"new THREE.CylinderGeometry(0, {r}, {h}, 16)"
    if shape == "sphere":
        r = dims[0]
        return f"new THREE.SphereGeometry({r}, 16, 12)"
    if shape == "plane":
        w, h = dims
        return f"new THREE.PlaneGeometry({w}, {h})"
    raise ValueError(f"Unknown shape: {shape!r}")


def _mat_js(mat: dict) -> str:
    """Return a Three.js MeshStandardMaterial constructor call."""
    color = _hex_to_js_int(mat["color"])
    roughness = mat.get("roughness", 0.85)
    metalness = mat.get("metalness", 0.05)
    props = f"color: {color}, roughness: {roughness}, metalness: {metalness}"
    if "emissive" in mat:
        em = _hex_to_js_int(mat["emissive"])
        ei = mat.get("emissive_intensity", 0.5)
        props += f", emissive: {em}, emissiveIntensity: {ei}"
    return f"new THREE.MeshStandardMaterial({{ {props} }})"


def build_body_from_packets(pieces: list, packets: dict) -> str:
    """Generate a Three.js buildModel() function body from solver pieces + geometry packets.

    pieces  — list of Piece objects from SceneResult.pieces
    packets — {piece_id: normalised_packet} from geometry_receiver.receive_all()

    Pieces without a geometry packet get a grey placeholder box so the scene
    is always fully populated even during partial authoring sessions.
    """
    lines = ["    function buildModel(scene) {", "        const g = new THREE.Group();", ""]

    for piece in pieces:
        pid = piece.id
        lines.append(f"        // piece {pid}: {piece.type} ({piece.label})")
        lines.append("        {")
        lines.append("            const pg = new THREE.Group();")
        lines.append(f"            pg.position.set({piece.gx}, {piece.gy}, {piece.gz});")
        # Each rot step is 90° around y-axis; Three.js uses radians
        rot_rad = piece.rot * 1.5707963267948966  # π/2
        lines.append(f"            pg.rotation.y = {rot_rad:.6f};")

        if pid in packets:
            for i, prim in enumerate(packets[pid]["primitives"]):
                px, py, pz = prim["position"]
                rx, ry, rz = [v * 0.017453292519943295 for v in prim["rotation"]]  # deg→rad
                lines.append(f"            const geo{i} = {_geo_js(prim['shape'], prim['dimensions'])};")
                lines.append(f"            const mat{i} = {_mat_js(prim['material'])};")
                lines.append(f"            const mesh{i} = new THREE.Mesh(geo{i}, mat{i});")
                lines.append(f"            mesh{i}.position.set({px}, {py}, {pz});")
                lines.append(f"            mesh{i}.rotation.set({rx:.6f}, {ry:.6f}, {rz:.6f});")
                lines.append(f"            mesh{i}.castShadow = true;")
                lines.append(f"            mesh{i}.receiveShadow = true;")
                lines.append(f"            pg.add(mesh{i});")
        else:
            # Placeholder: grey 0.5×1×0.5 box centred 0.5 above floor
            lines.append("            const geo0 = new THREE.BoxGeometry(0.5, 1.0, 0.5);")
            lines.append("            const mat0 = new THREE.MeshStandardMaterial({ color: 0x888888, roughness: 0.8 });")
            lines.append("            const mesh0 = new THREE.Mesh(geo0, mat0);")
            lines.append("            mesh0.position.set(0, 0.5, 0);")
            lines.append("            mesh0.castShadow = true;")
            lines.append("            mesh0.receiveShadow = true;")
            lines.append("            pg.add(mesh0);")

        lines.append("            g.add(pg);")
        lines.append("        }")
        lines.append("")

    lines.append("        scene.add(g);")
    lines.append("        return g;")
    lines.append("    }")
    return "\n".join(lines)


def generate_scene_html(
    scene_result,
    packets: dict,
    title: str = "3D Scene",
    bg_color: str = "#1a1a2e",
    show_grid: bool = True,
    show_axes: bool = False,
) -> str:
    """Generate a complete Three.js HTML page from a SceneResult + geometry packets.

    scene_result — SceneResult from solve_object_scene()
    packets      — {piece_id: normalised_packet} from geometry_receiver.receive_all()
                   May be partial; unpacketed pieces get a grey placeholder.
    """
    pieces = scene_result.pieces

    # Auto-position camera to frame the whole scene
    if pieces:
        cx = sum(p.gx for p in pieces) / len(pieces)
        cz = sum(p.gz for p in pieces) / len(pieces)
        spread = max(
            max(abs(p.gx - cx) for p in pieces),
            max(abs(p.gz - cz) for p in pieces),
            1,
        )
        cam_y = max(10, spread * 0.9)
        cam_z = cz + spread * 1.5
        camera_pos = (cx, cam_y, cam_z)
    else:
        camera_pos = (15, 15, 30)

    build_body = build_body_from_packets(pieces, packets)

    return generate_scaffold(
        title=title,
        camera_pos=camera_pos,
        bg_color=bg_color,
        show_grid=show_grid,
        show_axes=show_axes,
        build_body=build_body,
    )


def main():
    parser = argparse.ArgumentParser(description="Generate Three.js HTML scaffold")
    parser.add_argument("--out", default=None, help="Output file (default: stdout)")
    parser.add_argument("--title", default="3D Model")
    parser.add_argument("--camera-x", type=float, default=10)
    parser.add_argument("--camera-y", type=float, default=10)
    parser.add_argument("--camera-z", type=float, default=20)
    parser.add_argument("--bg", default="#1a1a2e")
    parser.add_argument("--no-grid", action="store_true")
    parser.add_argument("--no-axes", action="store_true")
    parser.add_argument("--grid-size", type=int, default=40)

    args = parser.parse_args()

    html = generate_scaffold(
        title=args.title,
        camera_pos=(args.camera_x, args.camera_y, args.camera_z),
        bg_color=args.bg,
        show_grid=not args.no_grid,
        show_axes=not args.no_axes,
        grid_size=args.grid_size,
    )

    if args.out:
        with open(args.out, "w") as f:
            f.write(html)
        print(f"Wrote {args.out}")
    else:
        print(html)


if __name__ == "__main__":
    main()

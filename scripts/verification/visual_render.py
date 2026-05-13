"""
visual_render — render a generated scene HTML in headless Chromium and
screenshot it from configurable angles.

Sits alongside braille_view, path_walk, and spatial_validate as the fourth
verification pillar — the one that catches what the others can't. ASCII tells
you placement is valid; a render tells you a piece is too small to see, a
roof has a hole, smoke looks like beads on a string, or a cluster reads as
"separate clumps" instead of "woods."

Hard requirement: `playwright` and the chromium browser must be installed.
    pip install playwright
    playwright install chromium

Usage as a module:
    from verification.visual_render import render_scene_views
    paths = render_scene_views(
        "scene.html", out_dir="renders/",
        scene_result=result,        # optional, enables auto-framing
        tag="v2",
        angles=None,                # default: hero, top, side_e, side_w, walk
    )
    # paths == {"hero": "renders/v2_hero.png", ...}

Usage as a CLI:
    python visual_render.py scene.html --tag v2 --angles hero,top
    python visual_render.py scene.html --tag v2 --angles all

The HTML is patched in-memory to expose `window.camera` / `window.controls`
so the camera can be programmatically positioned. Original file is not
modified — a `*_patched.html` is written next to it and used as the source.
"""
from __future__ import annotations

import os
import re
import sys
import math
import json
import argparse
import threading
import socketserver
import http.server
from dataclasses import dataclass
from typing import Iterable

# ────────────────────────────────────────────────────────────────────────────
# Camera angle definitions
# ────────────────────────────────────────────────────────────────────────────
@dataclass
class Angle:
    """A camera placement: position and look-at target, in centered scene space."""
    label: str
    cam: tuple
    target: tuple


def default_angles(scene_radius: float = 12.0,
                   cx: float = 0.0, cz: float = 0.0) -> list[Angle]:
    """Reasonable default angles, scaled by scene size and offset to centroid.

    `scene_radius` is the half-extent of the scene. `cx`/`cz` are the scene
    centroid in world space (scaffold uses raw grid coords, not origin-centred).
    """
    r = max(scene_radius, 5.0)
    return [
        # hero: 3/4 elevated, SE perspective — best showcase angle
        Angle("hero",   cam=(cx + r*1.10, r*0.85, cz + r*1.30), target=(cx, r*0.10, cz)),
        # top-down: catches layout / cluster geometry
        Angle("top",    cam=(cx + 0.01,   r*2.40, cz + 0.01),   target=(cx, 0, cz)),
        # straight on from south, moderate elevation
        Angle("front",  cam=(cx,          r*0.70, cz + r*1.70), target=(cx, r*0.15, cz)),
        # east profile — good for façade, gable end, smoke
        Angle("side_e", cam=(cx + r*1.55, r*0.50, cz),          target=(cx, r*0.20, cz)),
        # west profile — symmetric counterpart
        Angle("side_w", cam=(cx - r*1.55, r*0.50, cz),          target=(cx, r*0.20, cz)),
        # ground level, "walking up" from south — atmospheric check
        Angle("walk",   cam=(cx + r*0.20, 1.60,   cz + r*0.95), target=(cx, 1.5, cz)),
    ]


# ────────────────────────────────────────────────────────────────────────────
# HTML patching — expose camera/controls/scene as window globals so playwright
# can drive them. We mutate a copy of the HTML, never the original.
# ────────────────────────────────────────────────────────────────────────────
_PATCH_RULES = [
    # Minified scaffold (dropgrid_run.py output) uses `cam`, no spaces
    (r"const cam=new THREE\.PerspectiveCamera\(",
     "const cam=window.camera=new THREE.PerspectiveCamera("),
    # Unminified scaffold fallback uses `camera` with spaces
    (r"const camera = new THREE\.PerspectiveCamera\(",
     "const camera = window.camera = new THREE.PerspectiveCamera("),
    # Expose OrbitControls if present (not all scaffolds use it)
    (r"const controls = new OrbitControls\(",
     "const controls = window.controls = new OrbitControls("),
]


def _find_vendor_dir() -> str | None:
    """Walk up from this file looking for vendor/three.r128.min.js."""
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        candidate = os.path.join(here, "vendor", "three.r128.min.js")
        if os.path.exists(candidate):
            return os.path.join(here, "vendor")
        here = os.path.dirname(here)
    return None


# Minimal OrbitControls stub — enough for our scaffolds; not interactive,
# but prevents the `new OrbitControls(...)` call from throwing.
_ORBIT_STUB = """\
class OrbitControls {
    constructor(cam, dom) {
        this.target = new THREE.Vector3();
        this.enableDamping = false;
    }
    update() {}
    addEventListener() {}
    removeEventListener() {}
    dispose() {}
}
"""


def patch_html_for_camera_access(html: str, vendor_dir: str | None = None) -> str:
    """Patch scaffold HTML so camera is reachable as window.camera.

    Handles two scaffold styles:
    1. Old UMD style — <script src="/vendor/three.r128.min.js"> — inlines Three.js
       so file:// loading works without a server.
    2. New ES module style — <script type="importmap"> with CDN URLs — replaces the
       importmap + module imports with the local UMD build + an OrbitControls stub,
       then strips the ES import statements and converts the module script to a
       regular script.  Works offline, no server needed.

    Idempotent: if already patched, returns input unchanged.
    """
    if "window.camera" in html:
        return html

    if vendor_dir is None:
        vendor_dir = _find_vendor_dir()

    three_js = None
    if vendor_dir:
        three_path = os.path.join(vendor_dir, "three.r128.min.js")
        if os.path.exists(three_path):
            three_js = open(three_path).read()

    # ── Path 1: Old UMD scaffold — inline Three.js from vendor ───────────────
    if '<script src=' in html and 'three' in html and three_js:
        inline = f"<script>{three_js}</script>"
        html = re.sub(
            r'<script src="[^"]*three[^"]*\.js"></script>',
            lambda _: inline,
            html, count=1,
        )

    # ── Path 2: New ES module scaffold — importmap + CDN ─────────────────────
    if 'type="importmap"' in html or "type='importmap'" in html:
        if three_js is None:
            raise RuntimeError(
                "patch_html_for_camera_access: ES module scaffold detected but "
                "vendor/three.r128.min.js not found. Cannot patch offline.\n"
                "Run: (no install needed — vendor/ ships with the repo)"
            )
        inline_block = f"<script>{three_js}\n{_ORBIT_STUB}</script>"
        # Replace <script type="importmap">…</script> with the UMD inline block
        html = re.sub(
            r'<script\s+type=["\']importmap["\']>.*?</script>',
            lambda _: inline_block,
            html, flags=re.DOTALL, count=1,
        )
        # Remove ES module import statements (now unnecessary)
        html = re.sub(r"[ \t]*import \* as THREE from ['\"]three['\"];?\s*\n", "", html)
        html = re.sub(r"[ \t]*import \{[^}]+\} from ['\"]three/addons/[^'\"]*['\"];?\s*\n",
                      "", html)
        # Convert <script type="module"> to <script> so code runs in global scope
        html = re.sub(r'<script\s+type=["\']module["\']>', "<script>", html, count=1)

    # ── Camera / controls exposure (both paths) ───────────────────────────────
    out = html
    for pattern, replacement in _PATCH_RULES:
        out, _ = re.subn(pattern, replacement, out, count=1)
    if "window.camera" not in out:
        raise RuntimeError(
            "patch_html_for_camera_access: could not find a camera declaration.\n"
            "Expected `const cam=new THREE.PerspectiveCamera(` (minified) or\n"
            "`const camera = new THREE.PerspectiveCamera(` (unminified).\n"
            "The scaffold output may have changed — update _PATCH_RULES."
        )
    return out


# ────────────────────────────────────────────────────────────────────────────
# Scene radius — auto-derive from a SceneResult, fall back to default
# ────────────────────────────────────────────────────────────────────────────
def compute_scene_radius(scene_result=None, fallback: float = 12.0
                         ) -> tuple[float, float, float]:
    """Return (radius, cx, cz) for the scene.

    radius — half-extent of the scene in grid units
    cx, cz — scene centroid in world-space (scaffold places at raw grid coords)
    Returns (fallback, 0, 0) if scene_result is None or has no pieces.
    """
    if scene_result is None:
        return fallback, 0.0, 0.0
    pieces = getattr(scene_result, "pieces", None)
    if not pieces:
        return fallback, 0.0, 0.0
    cx = sum(p.gx for p in pieces) / len(pieces)
    cz = sum(p.gz for p in pieces) / len(pieces)
    spread = max(
        max(abs(p.gx - cx) for p in pieces),
        max(abs(p.gz - cz) for p in pieces),
        1.0,
    )
    return float(spread), float(cx), float(cz)


# ────────────────────────────────────────────────────────────────────────────
# Main entry point
# ────────────────────────────────────────────────────────────────────────────
def render_scene_views(
    html_path: str,
    out_dir: str,
    scene_result=None,
    angles: "list[Angle] | list[str] | str | None" = None,
    tag: str = "render",
    viewport: tuple = (1100, 700),
    wait_ms_initial: int = 1500,
    wait_ms_per_angle: int = 500,
    headless: bool = True,
    log_console: bool = False,
) -> dict[str, str]:
    """Render `html_path` from each angle and save PNGs into `out_dir`.

    Returns a dict mapping angle label → output file path.

    Args:
        html_path: scaffold-generated HTML (won't be modified).
        out_dir: where PNGs go. Created if missing.
        scene_result: optional SceneResult — used for auto-framing the
            default angles. If omitted, a generic radius is used.
        angles: one of:
            None → use all default angles
            str like "hero,top" → subset of default angle labels
            str "all" → all default angles
            list of Angle objects → fully custom
            list of str → subset of default angle labels
        tag: prefix for output filenames (e.g. "v2" → v2_hero.png).
        viewport: (width, height) in pixels.
        wait_ms_initial: ms to wait after page load for Three.js to render.
        wait_ms_per_angle: ms to wait after camera move before screenshotting.
        headless: run Chromium headless (default True). Set False to debug.
        log_console: if True, print browser console errors/warnings.
    """
    # Lazy import — playwright is a hard dep but we want a clean error if missing
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError(
            "render_scene_views requires playwright. Install with:\n"
            "    pip install playwright\n"
            "    playwright install chromium"
        ) from e

    # Resolve angles
    radius, cx, cz = compute_scene_radius(scene_result)
    defaults = default_angles(radius, cx, cz)
    defaults_by_label = {a.label: a for a in defaults}

    if angles is None or angles == "all":
        resolved = defaults
    elif isinstance(angles, str):
        labels = [s.strip() for s in angles.split(",") if s.strip()]
        resolved = [defaults_by_label[l] for l in labels]
    elif isinstance(angles, list):
        resolved = []
        for a in angles:
            if isinstance(a, Angle):
                resolved.append(a)
            elif isinstance(a, str):
                resolved.append(defaults_by_label[a])
            else:
                raise TypeError(f"angles[i] must be Angle or str, got {type(a).__name__}")
    else:
        raise TypeError(f"angles must be None/str/list, got {type(angles).__name__}")

    # Patch the HTML so the camera is reachable
    with open(html_path) as f:
        original_html = f.read()
    patched_html = patch_html_for_camera_access(original_html)
    patched_path = html_path.replace(".html", "_patched.html")
    if not patched_path.endswith(".html"):
        patched_path = html_path + ".patched"
    with open(patched_path, "w") as f:
        f.write(patched_html)

    os.makedirs(out_dir, exist_ok=True)
    _server = None
    url = "file://" + os.path.abspath(patched_path)

    output_paths: dict[str, str] = {}

    # Find chromium — prefer system playwright install, fall back to node playwright
    _known_paths = [
        "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
        "/opt/pw-browsers/chromium/chrome-linux/chrome",
    ]
    _exec = next((p for p in _known_paths if os.path.exists(p)), None)

    with sync_playwright() as p:
        launch_kwargs = dict(
            headless=headless,
            args=["--use-gl=swiftshader", "--enable-webgl"],
        )
        if _exec:
            launch_kwargs["executable_path"] = _exec
        browser = p.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": viewport[0], "height": viewport[1]})

        if log_console:
            page.on("console", lambda m: print(f"[{m.type}] {m.text}")
                    if m.type in ("error", "warning") else None)
            page.on("pageerror", lambda e: print(f"[pageerror] {e}"))

        page.goto(url)
        page.wait_for_timeout(wait_ms_initial)

        # Sanity check
        ok = page.evaluate("!!(window.camera)")
        if not ok:
            browser.close()
            raise RuntimeError(
                "Page loaded but window.camera not found. "
                "Patch may have failed — check scaffold output structure."
            )
        has_controls = page.evaluate("!!(window.controls)")

        for ang in resolved:
            cx, cy, cz = ang.cam
            tx, ty, tz = ang.target
            page.evaluate(f"""
                window.camera.position.set({cx}, {cy}, {cz});
                window.camera.lookAt({tx}, {ty}, {tz});
                if (window.controls) {{
                    window.controls.target.set({tx}, {ty}, {tz});
                    window.controls.update();
                }}
            """)
            page.wait_for_timeout(wait_ms_per_angle)
            out = os.path.join(out_dir, f"{tag}_{ang.label}.png")
            page.screenshot(path=out)
            output_paths[ang.label] = out

        browser.close()

    if _server is not None:
        _server.shutdown()

    return output_paths


# ────────────────────────────────────────────────────────────────────────────
# Local HTTP server helper for ES module scaffolds
# ────────────────────────────────────────────────────────────────────────────
def _start_local_server(directory: str) -> tuple:
    """Start a background HTTP server serving `directory`. Returns (server, port)."""
    class _QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args): pass
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

    server = socketserver.TCPServer(("127.0.0.1", 0), _QuietHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


# ────────────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Render a scene HTML from configurable angles."
    )
    parser.add_argument("html", help="Path to scaffold-generated HTML.")
    parser.add_argument("--out-dir", default="renders",
                        help="Output directory for PNGs (default: renders/).")
    parser.add_argument("--tag", default="render",
                        help="Filename prefix (default: render).")
    parser.add_argument("--angles", default="all",
                        help="Comma-separated list of angle labels, or 'all' "
                             "(default). Available: hero, top, front, side_e, "
                             "side_w, walk.")
    parser.add_argument("--viewport", default="1100x700",
                        help="WxH in pixels (default 1100x700).")
    parser.add_argument("--scene-radius", type=float, default=None,
                        help="Override auto-framing radius.")
    parser.add_argument("--log-console", action="store_true",
                        help="Print browser console errors/warnings.")
    args = parser.parse_args()

    w, h = (int(x) for x in args.viewport.lower().split("x"))

    # If scene_radius was given, build angles from it explicitly
    if args.scene_radius is not None:
        custom_angles = default_angles(args.scene_radius)
        # filter by label list
        if args.angles != "all":
            keep = {s.strip() for s in args.angles.split(",")}
            custom_angles = [a for a in custom_angles if a.label in keep]
        result = render_scene_views(
            args.html, out_dir=args.out_dir, tag=args.tag,
            angles=custom_angles, viewport=(w, h),
            log_console=args.log_console,
        )
    else:
        result = render_scene_views(
            args.html, out_dir=args.out_dir, tag=args.tag,
            angles=args.angles, viewport=(w, h),
            log_console=args.log_console,
        )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

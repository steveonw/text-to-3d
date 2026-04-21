#!/usr/bin/env python3
"""
try_now.py — Local demo server for text-to-3D scene generation.

Usage:
  python try_now.py
  python try_now.py --port 8080

Then open http://localhost:8000 in your browser.
"""

import sys
import json
import argparse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from io import StringIO

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

from dropgrid.api import solve_object_scene
from dropgrid_run import EXAMPLES, render_html

# ── Landing page ──────────────────────────────────────────────────────────────

LANDING_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>text-to-3d · Try Now</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0 }
  body {
    font-family: 'Courier New', Courier, monospace;
    background: #111a11;
    color: #c8d8b8;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }
  header {
    padding: 24px 32px 16px;
    border-bottom: 1px solid #2a3a2a;
  }
  h1 { font-size: 1.1rem; color: #8aaa7a; letter-spacing: 0.05em }
  .subtitle { font-size: 0.78rem; color: #5a7a5a; margin-top: 4px }
  main {
    display: flex;
    flex: 1;
    overflow: hidden;
  }
  .sidebar {
    width: 360px;
    min-width: 280px;
    flex-shrink: 0;
    padding: 20px 24px;
    border-right: 1px solid #2a3a2a;
    display: flex;
    flex-direction: column;
    gap: 18px;
    overflow-y: auto;
  }
  .section-label {
    font-size: 0.7rem;
    color: #5a7a5a;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 8px;
  }
  .examples {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .example-btn {
    background: #1a2a1a;
    border: 1px solid #3a5a3a;
    color: #9ab88a;
    padding: 8px 12px;
    cursor: pointer;
    text-align: left;
    font-family: inherit;
    font-size: 0.8rem;
    border-radius: 3px;
    transition: background 0.15s, border-color 0.15s;
  }
  .example-btn:hover { background: #223022; border-color: #5a8a5a }
  .example-btn.active { background: #2a3a2a; border-color: #6a9a6a; color: #c8e8b8 }
  .example-btn .name { font-weight: bold }
  .example-btn .desc { color: #5a7a5a; font-size: 0.72rem; margin-top: 2px }
  textarea {
    width: 100%;
    height: 180px;
    background: #0e180e;
    border: 1px solid #2a4a2a;
    color: #a8c898;
    font-family: inherit;
    font-size: 0.78rem;
    padding: 10px;
    resize: vertical;
    outline: none;
    border-radius: 3px;
    line-height: 1.5;
  }
  textarea:focus { border-color: #4a7a4a }
  .dsl-hint { font-size: 0.7rem; color: #3a5a3a; margin-top: 4px; line-height: 1.5 }
  .generate-btn {
    background: #2a5a2a;
    border: 1px solid #4a9a4a;
    color: #c8f8c8;
    padding: 10px 18px;
    cursor: pointer;
    font-family: inherit;
    font-size: 0.85rem;
    border-radius: 3px;
    width: 100%;
    transition: background 0.15s;
  }
  .generate-btn:hover { background: #3a6a3a }
  .generate-btn:disabled { opacity: 0.4; cursor: default }
  .status {
    font-size: 0.75rem;
    color: #5a7a5a;
    min-height: 1.4em;
  }
  .status.error { color: #c86060 }
  .preview {
    flex: 1;
    position: relative;
    background: #0a120a;
  }
  iframe {
    width: 100%;
    height: 100%;
    border: none;
    display: block;
  }
  .placeholder {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #2a4a2a;
    font-size: 0.85rem;
    gap: 12px;
    pointer-events: none;
  }
  .placeholder .big { font-size: 3rem }
  .controls-hint {
    font-size: 0.7rem;
    color: #3a5a3a;
    text-align: center;
    line-height: 1.6;
  }
</style>
</head>
<body>
<header>
  <h1>text-to-3d · Try Now</h1>
  <div class="subtitle">Pick an example or write DSL → generate a walkable 3D scene</div>
</header>
<main>
  <div class="sidebar">
    <div>
      <div class="section-label">Built-in examples</div>
      <div class="examples" id="examples"></div>
    </div>
    <div>
      <div class="section-label">Custom DSL</div>
      <textarea id="dsl" placeholder="anchor campfire center&#10;object tree label forest count 8 shape circle radius 5&#10;object road label path count 8 from center heading south steps 8&#10;..."></textarea>
      <div class="dsl-hint">
        Modes: scatter · cluster · line · circle · follow · rect_perimeter · rect_fill · attach · center<br>
        Types: campfire · tree · road · lantern · log · fence · wall · house · rubble · gate · tower · table
      </div>
    </div>
    <div>
      <button class="generate-btn" id="gen-btn" onclick="generate()">Generate scene</button>
      <div class="status" id="status"></div>
    </div>
    <div class="controls-hint">
      In the scene: drag to orbit · scroll to zoom<br>
      Press <b>F</b> for first-person walk mode (WASD + mouse)
    </div>
  </div>
  <div class="preview">
    <div class="placeholder" id="placeholder">
      <div class="big">⬡</div>
      <div>Pick an example or write DSL, then Generate</div>
    </div>
    <iframe id="preview" style="display:none"></iframe>
  </div>
</main>
<script>
const EXAMPLES = EXAMPLES_JSON;
let activeExample = null;

const examplesEl = document.getElementById('examples');
for (const [key, ex] of Object.entries(EXAMPLES)) {
  const btn = document.createElement('button');
  btn.className = 'example-btn';
  btn.dataset.key = key;
  btn.innerHTML = `<div class="name">${key.replace(/_/g,' ')}</div><div class="desc">${ex.story.slice(0, 60)}…</div>`;
  btn.onclick = () => selectExample(key);
  examplesEl.appendChild(btn);
}

function selectExample(key) {
  activeExample = key;
  document.querySelectorAll('.example-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.key === key)
  );
  document.getElementById('dsl').value = EXAMPLES[key].intent.trim();
}

async function generate() {
  const dsl = document.getElementById('dsl').value.trim();
  if (!dsl) { setStatus('Enter some DSL first.', true); return; }

  const btn = document.getElementById('gen-btn');
  btn.disabled = true;
  setStatus('Solving scene…');

  try {
    const body = activeExample
      ? JSON.stringify({ example: activeExample })
      : JSON.stringify({ intent: dsl });

    const res = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
    });
    const data = await res.json();
    if (data.error) { setStatus('Error: ' + data.error, true); return; }

    const frame = document.getElementById('preview');
    frame.srcdoc = data.html;
    frame.style.display = 'block';
    document.getElementById('placeholder').style.display = 'none';
    setStatus(`${data.pieces} pieces placed · drag to orbit · F for walk mode`);
    activeExample = null; // reset so next edit uses custom DSL
    document.querySelectorAll('.example-btn').forEach(b => b.classList.remove('active'));
  } catch (e) {
    setStatus('Server error: ' + e.message, true);
  } finally {
    btn.disabled = false;
  }
}

function setStatus(msg, isError = false) {
  const el = document.getElementById('status');
  el.textContent = msg;
  el.className = 'status' + (isError ? ' error' : '');
}

// Allow Ctrl+Enter to generate
document.getElementById('dsl').addEventListener('keydown', e => {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) generate();
});
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            examples_for_js = {
                k: {"story": v["story"], "intent": v["intent"]}
                for k, v in EXAMPLES.items()
            }
            html = LANDING_HTML.replace(
                "EXAMPLES_JSON", json.dumps(examples_for_js)
            )
            body = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/generate":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                self._json_error("Invalid JSON", 400)
                return

            example = data.get("example", "")
            if example and example in EXAMPLES:
                intent = EXAMPLES[example]["intent"]
                title = example.replace("_", " ").title()
            else:
                intent = data.get("intent", "").strip()
                title = "Custom Scene"

            if not intent:
                self._json_error("No DSL provided", 400)
                return

            try:
                # Suppress debug output from solver
                old_stdout = sys.stdout
                sys.stdout = StringIO()
                result = solve_object_scene(intent, seed=42, debug=False)
                sys.stdout = old_stdout

                html = render_html(result, title=title)
                response = json.dumps({"html": html, "pieces": len(result.pieces)})
                body = response.encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as exc:
                sys.stdout = old_stdout if "old_stdout" in dir() else sys.stdout
                self._json_error(str(exc), 500)
        else:
            self.send_response(404)
            self.end_headers()

    def _json_error(self, msg, code=500):
        body = json.dumps({"error": msg}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} {fmt % args}")


def main():
    ap = argparse.ArgumentParser(description="text-to-3d local demo server")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    args = ap.parse_args()

    url = f"http://localhost:{args.port}"
    server = HTTPServer(("", args.port), Handler)
    print(f"text-to-3d · Try Now")
    print(f"  {url}")
    print(f"  Ctrl+C to stop")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()

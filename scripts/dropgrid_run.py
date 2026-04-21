#!/usr/bin/env python3
"""
dropgrid_run.py — Story to rendered 3D scene.

Usage:
  python dropgrid_run.py                          # interactive mode
  python dropgrid_run.py --scene shrine.txt       # from file
  python dropgrid_run.py --example shrine         # built-in example
  python dropgrid_run.py --list                   # list examples

Pipeline:
  Story → Intent (object DSL) → Python Solver → ASCII Map → Three.js HTML
"""

import json, sys, os
from pathlib import Path

# Add scripts to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))

from dropgrid.api import solve_object_scene

# ═══════════════════════════════════════════════════════════
# BUILT-IN EXAMPLE SCENES
# ═══════════════════════════════════════════════════════════
EXAMPLES = {
    "shrine": {
        "story": "A forest shrine deep in the woods. Stone altar in a clearing. Path leads in from the south. Lanterns guide the way. Trees press in from all sides. Standing stones mark the sacred boundary.",
        "intent": """
anchor campfire altar
ma hard radius 4

object road label path count 14 from altar heading south steps 14 wobble 0.15
object lantern label lanterns count 6 target road side any distance 1 spacing 2
object tree label forest count 12 shape circle radius 7 clusters 6 spread 1
object log label logs count 3 target road side any distance 2 spacing 4
object fence label stones count 8 shape circle radius 5 clusters 8 spread 0
object rubble label offerings count 3 radius 12
""",
    },
    "village": {
        "story": "A farming village. Well in the center square. Barn to the north with a fenced yard. Path from the well toward the barn. Houses cluster near the well. Trees scattered for shade.",
        "intent": """
anchor campfire well
ma hard radius 4

object road label path count 10 from well heading north steps 10 wobble 0.2
object fence label yard count 12 shape circle radius 8 clusters 6 spread 1
object tree label trees count 6 target road side any distance 4 spacing 1
object rubble label clutter count 3 radius 12
""",
    },
    "graveyard": {
        "story": "An old graveyard. Central crypt for the town founder. Gravestones in rows. Iron fence perimeter with a gate on the south side. Dead trees nobody cut down. Lanterns for mourners.",
        "intent": """
anchor tower crypt
ma hard radius 4

object fence label iron_fence count 14 shape circle radius 10 clusters 7 spread 1
object fence label gravestones count 12 shape circle radius 6 clusters 4 spread 1
object lantern label lanterns count 4 shape circle radius 8 clusters 4 spread 0
object tree label dead_trees count 4 radius 14
object rubble label rubble count 3 radius 12
""",
    },
    "walled_city": {
        "story": "A small walled settlement. Tower at center. Walls in clusters around it. Outer fence ring. Houses between walls and fences. Rubble from age.",
        "intent": """
anchor tower keep
ma hard radius 4

object wall label walls count 16 target keep shape circle radius 7 clusters 4 spread 1 arc 0.85
object fence label fences count 12 target keep shape circle radius 10 clusters 4 spread 1
object house label houses count 4 target keep shape circle radius 4 spread 1
object rubble label rubble count 3 radius 12
""",
    },
    "campsite": {
        "story": "A traveler's campsite by the road. Campfire in the middle. Tents around it. Logs for sitting. A few barrels of supplies. The road passes nearby.",
        "intent": """
anchor campfire fire
ma hard radius 3

object road label road count 12 from fire heading east steps 12 wobble 0.3
object fence label tents count 4 shape circle radius 4 clusters 4 spread 0
object log label seats count 4 shape circle radius 2 clusters 4 spread 0
object rubble label supplies count 3 radius 6
""",
    },
}

# ═══════════════════════════════════════════════════════════
# THREE.JS RENDERER TEMPLATE
# ═══════════════════════════════════════════════════════════
RENDERER_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title} — Drop Grid</title>
<style>*{{margin:0;padding:0}}body{{overflow:hidden;background:#1a2a1a}}canvas{{display:block}}
#info{{position:fixed;bottom:12px;left:12px;color:#8a9a7a;font:11px/1.4 'Courier New',monospace;background:rgba(0,0,0,0.6);padding:8px 12px;border-radius:4px;pointer-events:none}}
</style>
</head>
<body>
<canvas id="cv"></canvas>
<div id="info">{title} · {count} pieces · Drop Grid</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
const D={pieces_json};
const canvas=document.getElementById('cv');
const scene=new THREE.Scene();
const cam=new THREE.PerspectiveCamera(50,innerWidth/innerHeight,0.1,200);
const ren=new THREE.WebGLRenderer({{canvas,antialias:true}});
ren.setSize(innerWidth,innerHeight);ren.setPixelRatio(Math.min(devicePixelRatio,2));
ren.shadowMap.enabled=true;ren.shadowMap.type=THREE.PCFSoftShadowMap;
ren.toneMapping=THREE.ACESFilmicToneMapping;ren.toneMappingExposure=0.95;
scene.background=new THREE.Color(0x1a2a1a);
scene.fog=new THREE.FogExp2(0x1a2a1a,0.02);
scene.add(new THREE.AmbientLight(0x445544,0.5));
const sun=new THREE.DirectionalLight(0xeeddaa,0.9);
sun.position.set(8,18,-5);sun.castShadow=true;
sun.shadow.mapSize.set(2048,2048);scene.add(sun);
scene.add(new THREE.HemisphereLight(0x445544,0x332211,0.4));
let seed=777;function rng(){{seed=(seed*1664525+1013904223)&0x7fffffff;return seed/0x7fffffff}}
function add(geo,color,x,y,z,opts={{}}){{
  const mat=new THREE.MeshStandardMaterial({{color,roughness:opts.rough||0.85,metalness:opts.metal||0.05}});
  if(opts.emissive){{mat.emissive=new THREE.Color(opts.emissive);mat.emissiveIntensity=opts.emissiveI||0.5}}
  const m=new THREE.Mesh(geo,mat);m.position.set(x,y,z);
  if(opts.ry)m.rotation.y=opts.ry;if(opts.rx)m.rotation.x=opts.rx;if(opts.rz)m.rotation.z=opts.rz;
  m.castShadow=true;m.receiveShadow=true;scene.add(m);return m;
}}
// Ground
const gg=new THREE.PlaneGeometry(34,34,16,16);
const gp=gg.attributes.position;
for(let i=0;i<gp.count;i++)gp.setZ(i,Math.sin(gp.getX(i)*0.5)*Math.cos(gp.getY(i)*0.4)*0.1);
gg.computeVertexNormals();
add(gg,0x2a3a22,15,-0.02,15,{{rx:-Math.PI/2,rough:1}});
for(let i=0;i<25;i++){{const s=0.5+rng()*1.5;add(new THREE.CircleGeometry(s/2,6),rng()>0.5?0x1a2a15:0x2a3a1a,2+rng()*28,0.005,2+rng()*28,{{rx:-Math.PI/2}})}}
const gi=new THREE.InstancedMesh(new THREE.ConeGeometry(0.03,0.12,3),new THREE.MeshStandardMaterial({{color:0x2a4a1e,roughness:1}}),300);
const dm=new THREE.Object3D();
for(let i=0;i<300;i++){{dm.position.set(rng()*30,0.06,rng()*30);dm.rotation.set(0,rng()*3,(rng()-0.5)*0.3);dm.scale.setScalar(0.3+rng()*1.5);dm.updateMatrix();gi.setMatrixAt(i,dm.matrix)}}
scene.add(gi);
const GEN={{
  campfire(p){{add(new THREE.CylinderGeometry(0.9,1.1,0.5,8),0x6a6a60,p.x,0.25,p.z);add(new THREE.CylinderGeometry(0.6,0.7,0.3,6),0x7a7a6e,p.x,0.55,p.z);add(new THREE.TorusGeometry(0.35,0.03,4,12),0x5a5a50,p.x,0.72,p.z,{{rx:Math.PI/2}});add(new THREE.ConeGeometry(0.12,0.35,5),0xff6622,p.x,0.9,p.z,{{emissive:0xff4400,emissiveI:1}});for(let i=0;i<5;i++){{const a=i/5*Math.PI*2;add(new THREE.SphereGeometry(0.1+rng()*0.08,5,4),0x5a5a50,p.x+Math.cos(a)*0.85,0.12,p.z+Math.sin(a)*0.85)}};const l=new THREE.PointLight(0xff8844,0.6,15);l.position.set(p.x,1.5,p.z);scene.add(l)}},
  tower(p){{add(new THREE.CylinderGeometry(1.2,1.5,4,8),0x6a6a5e,p.x,2,p.z);add(new THREE.ConeGeometry(1.6,1.5,8),0x5a4a3a,p.x,4.5,p.z);add(new THREE.BoxGeometry(0.5,1.2,0.06),0x4a3020,p.x,0.6,p.z+1.5)}},
  road(p){{const s=0.3+rng()*0.2;add(new THREE.CylinderGeometry(s,s+0.05,0.07,6),[0x5a5a50,0x4a5a48,0x5a6a55][Math.floor(rng()*3)],p.x+(rng()-0.5)*0.2,0.035,p.z+(rng()-0.5)*0.2,{{ry:rng()*3}});add(new THREE.CircleGeometry(0.5,6),0x2a2a1a,p.x,0.004,p.z,{{rx:-Math.PI/2}})}},
  lantern(p){{const x=p.x,z=p.z;add(new THREE.CylinderGeometry(0.2,0.25,0.15,6),0x6a6a5e,x,0.075,z);add(new THREE.CylinderGeometry(0.06,0.07,0.7,6),0x7a7a6e,x,0.5,z);add(new THREE.BoxGeometry(0.25,0.25,0.25),0x8a8a7e,x,0.95,z);add(new THREE.SphereGeometry(0.08,6,4),0xffaa44,x,0.95,z,{{emissive:0xff8833,emissiveI:1.2}});add(new THREE.ConeGeometry(0.22,0.15,4),0x5a5a50,x,1.15,z,{{ry:Math.PI/4}});const l=new THREE.PointLight(0xff9944,0.15,4);l.position.set(x,0.95,z);scene.add(l)}},
  tree(p){{const x=p.x,z=p.z,h=3.5+rng()*3;add(new THREE.CylinderGeometry(0.1,0.22,h,7),0x3a2a1a,x,h/2,z,{{rz:(rng()-0.5)*0.04}});const cr=1+rng()*0.7;add(new THREE.SphereGeometry(cr,8,6),0x1a3a12,x,h+cr*0.3,z);add(new THREE.SphereGeometry(cr*0.8,7,5),0x2a4a1a,x+0.25,h+cr*0.7,z-0.15);add(new THREE.SphereGeometry(cr*0.6,6,4),0x1a3010,x-0.2,h+cr*0.1,z+0.2)}},
  log(p){{const a=rng()*Math.PI,l=0.8+rng()*0.6;add(new THREE.CylinderGeometry(0.08,0.1,l,6),0x4a3a2a,p.x,0.1,p.z,{{rx:Math.PI/2,ry:a}});add(new THREE.SphereGeometry(0.06,4,3),0x3a5a2a,p.x+(rng()-0.5)*0.2,0.15,p.z+(rng()-0.5)*0.2)}},
  fence(p){{const x=p.x,z=p.z,h=0.8+rng()*1,w=0.2+rng()*0.15;add(new THREE.BoxGeometry(w,h,w*0.7),0x6a6a5e,x,h/2,z,{{ry:rng()*Math.PI,rz:(rng()-0.5)*0.08}});add(new THREE.SphereGeometry(w*0.8,5,3),0x3a5a2a,x,0.08,z)}},
  wall(p){{const x=p.x,z=p.z;add(new THREE.BoxGeometry(1,1.8,0.4),0x6a6a5e,x,0.9,z,{{ry:p.r*Math.PI/2}});add(new THREE.BoxGeometry(1.1,0.15,0.5),0x5a5a50,x,0,z,{{ry:p.r*Math.PI/2}})}},
  house(p){{const x=p.x,z=p.z;add(new THREE.BoxGeometry(1.8,1.7,1.6),0x9a7a55,x,0.85,z);add(new THREE.ConeGeometry(1.4,1,4),0x6a4a3a,x,2.2,z,{{ry:Math.PI/4}});add(new THREE.BoxGeometry(0.4,0.95,0.06),0x4a3020,x,0.47,z+0.8)}},
  rubble(p){{const n=2+Math.floor(rng()*3);for(let i=0;i<n;i++){{const s=0.05+rng()*0.12;add(rng()>0.5?new THREE.BoxGeometry(s,s*0.6,s):new THREE.SphereGeometry(s/2,4,3),rng()>0.5?0x6a6a5e:0x5a5a48,p.x+(rng()-0.5)*0.5,s*0.3,p.z+(rng()-0.5)*0.5,{{ry:rng()*3}})}}}},
  gate(p){{const x=p.x,z=p.z;add(new THREE.BoxGeometry(0.15,1.5,0.15),0x5a5a50,x-0.5,0.75,z);add(new THREE.BoxGeometry(0.15,1.5,0.15),0x5a5a50,x+0.5,0.75,z);add(new THREE.BoxGeometry(1.2,0.1,0.1),0x5a5a50,x,1.5,z)}},
  table(p){{add(new THREE.BoxGeometry(1.2,0.08,0.8),0x6a5a4a,p.x,0.75,p.z);for(let i=0;i<4;i++){{const ox=i<2?-0.45:0.45,oz=i%2==0?-0.3:0.3;add(new THREE.CylinderGeometry(0.03,0.03,0.7,4),0x5a4a3a,p.x+ox,0.37,p.z+oz)}}}},
}};
for(const p of D){{const g=GEN[p.t];if(g)g(p)}}
const cx=15,cz=15;let theta=Math.PI*0.3,phi=Math.PI/3.2,radius=25;
const tgt=new THREE.Vector3(cx,1.5,cz);
function uc(){{cam.position.set(tgt.x+radius*Math.sin(phi)*Math.cos(theta),tgt.y+radius*Math.cos(phi),tgt.z+radius*Math.sin(phi)*Math.sin(theta));cam.lookAt(tgt)}}
uc();let dr=false,px,py;
canvas.addEventListener('pointerdown',e=>{{dr=true;px=e.clientX;py=e.clientY}});
addEventListener('pointermove',e=>{{if(!dr)return;theta+=(e.clientX-px)*0.008;phi=Math.max(0.15,Math.min(1.45,phi+(e.clientY-py)*0.008));px=e.clientX;py=e.clientY;uc()}});
addEventListener('pointerup',()=>dr=false);
canvas.addEventListener('wheel',e=>{{radius=Math.max(6,Math.min(50,radius+e.deltaY*0.03));uc()}},{{passive:true}});
addEventListener('resize',()=>{{cam.aspect=innerWidth/innerHeight;cam.updateProjectionMatrix();ren.setSize(innerWidth,innerHeight)}});
let t=0;(function a(){{requestAnimationFrame(a);t+=0.05;ren.render(scene,cam)}})();
</script>
</body>
</html>'''


def solve_and_report(intent_text, seed=42):
    """Solve a scene, print ASCII, return result."""
    result = solve_object_scene(intent_text, seed=seed, debug=True)
    
    conns = result.meta.get('connections', [])
    nc = len(conns) if isinstance(conns, list) else conns
    warns = result.meta.get('warnings', [])
    
    from collections import Counter
    types = Counter(p.type for p in result.pieces)
    
    print(f"Placed: {len(result.pieces)}  Connections: {nc}  Warnings: {len(warns)}")
    print(f"Types: {dict(types)}")
    for w in warns:
        print(f"  ⚠ {w}")
    print()
    print(result.to_ascii(include_legend=True))
    
    return result


def render_html(result, title="Scene"):
    """Generate standalone Three.js HTML from solver result."""
    pieces = []
    for p in result.pieces:
        pieces.append({
            't': p.type, 'x': p.gx + 0.5, 'z': p.gz + 0.5,
            'r': p.rot, 'label': p.label
        })
    
    pieces_json = json.dumps(pieces)
    html = RENDERER_TEMPLATE.format(
        title=title,
        count=len(pieces),
        pieces_json=pieces_json,
    )
    return html


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Drop Grid — Story to 3D Scene")
    ap.add_argument("--example", help="Built-in example name")
    ap.add_argument("--scene", help="Scene file (.txt with object DSL)")
    ap.add_argument("--list", action="store_true", help="List built-in examples")
    ap.add_argument("--seed", type=int, default=42, help="Random seed")
    ap.add_argument("--output", help="Output HTML filename")
    ap.add_argument("--ascii-only", action="store_true", help="Only print ASCII, no HTML")
    args = ap.parse_args()

    if args.list:
        print("Built-in examples:")
        for name, data in EXAMPLES.items():
            print(f"  {name:15} — {data['story'][:60]}...")
        return

    # Get intent
    if args.example:
        if args.example not in EXAMPLES:
            print(f"Unknown example: {args.example}")
            print(f"Available: {', '.join(EXAMPLES.keys())}")
            return
        ex = EXAMPLES[args.example]
        title = args.example.replace("_", " ").title()
        intent = ex["intent"]
        print(f"Story: {ex['story']}")
        print()
    elif args.scene:
        with open(args.scene) as f:
            intent = f.read()
        title = Path(args.scene).stem.replace("_", " ").title()
    else:
        print("Drop Grid — Story to 3D Scene")
        print("Usage:")
        print("  python dropgrid_run.py --example shrine")
        print("  python dropgrid_run.py --scene my_scene.txt")
        print("  python dropgrid_run.py --list")
        return

    # Solve
    print(f"=== {title} ===")
    result = solve_and_report(intent, seed=args.seed)

    # Render
    if not args.ascii_only:
        html = render_html(result, title=title)
        out_path = args.output or f"{args.example or 'scene'}.html"
        with open(out_path, 'w') as f:
            f.write(html)
        print(f"\nRendered: {out_path} ({len(html)//1024}KB)")
        print("Open in browser to view 3D scene. Drag to orbit, scroll to zoom.")


if __name__ == "__main__":
    main()

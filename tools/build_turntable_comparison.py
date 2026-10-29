"""Package exact Blender frames as a synchronized 360 comparison and viewer."""
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "turntable"
legacy = [OUT / "legacy" / "head" / f"frame-{i:02d}.png" for i in range(24)]
ours = [OUT / "ours" / "head" / f"frame-{i:02d}.png" for i in range(24)]
full = [OUT / "legacy" / "full" / f"frame-{i:02d}.png" for i in range(24)]
for path in legacy + ours + full:
    if not path.is_file():
        raise FileNotFoundError(path)

comparisons = []
for left, right in zip(legacy, ours):
    with Image.open(left) as a, Image.open(right) as b:
        sheet = Image.new("RGB", (a.width + b.width, max(a.height, b.height)), "white")
        sheet.paste(a.convert("RGB"), (0, 0))
        sheet.paste(b.convert("RGB"), (a.width, 0))
        comparisons.append(sheet)
gif = OUT / "head-comparison-360.gif"
comparisons[0].save(gif, save_all=True, append_images=comparisons[1:], duration=180, loop=0, optimize=True)
for frame in comparisons:
    frame.close()

with Image.open(full[0]) as first:
    frames = [first.convert("RGB")]
for path in full[1:]:
    with Image.open(path) as image:
        frames.append(image.convert("RGB"))
full_gif = OUT / "legacy-full-360.gif"
frames[0].save(full_gif, save_all=True, append_images=frames[1:], duration=180, loop=0, optimize=True)
for frame in frames:
    frame.close()

html = """<!doctype html>
<html lang="pt-BR"><meta charset="utf-8"><title>Budge Dragon — comparação 360°</title>
<style>
body{font:16px system-ui;background:#17181b;color:#eee;margin:24px;max-width:1600px}
h1{font-size:25px;margin:0 0 8px}p{line-height:1.45;color:#bbb}
.controls{display:flex;gap:16px;align-items:center;margin:18px 0}input{width:min(700px,65vw)}button{font:inherit;padding:7px 16px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:16px}.panel{background:#25262a;padding:12px;border-radius:8px}
.panel img{width:100%;height:auto;display:block}.panel h2{font-size:17px;margin:0 0 10px}
.full{max-width:650px;margin-top:18px}
@media(max-width:850px){.row{grid-template-columns:1fr}}
</style>
<h1>Budge Dragon — comparação 360°</h1>
<p>Esquerda: GLB herdado completo, recorte da cabeça. Direita: nosso estudo de mandíbula e cabeça, ainda isolado e sem textura final. Ambos usam a mesma câmera, escala, luz e pose de repouso. A vista inferior mostra o corpo inteiro do legado.</p>
<div class="controls"><button id="play">Pausar</button><input id="angle" type="range" min="0" max="23" value="0"><output id="degree">0°</output></div>
<div class="row"><div class="panel"><h2>Legado — cabeça e pescoço</h2><img id="legacy" src="legacy/head/frame-00.png"></div>
<div class="panel"><h2>Nosso estudo — cabeça isolada</h2><img id="ours" src="ours/head/frame-00.png"></div></div>
<div class="panel full"><h2>Legado — corpo inteiro</h2><img id="full" src="legacy/full/frame-00.png"></div>
<script>
const slider=document.getElementById('angle'), degree=document.getElementById('degree'), play=document.getElementById('play');
let running=true;function show(){let n=+slider.value,s=String(n).padStart(2,'0');degree.textContent=(n*15)+'°';
document.getElementById('legacy').src='legacy/head/frame-'+s+'.png';
document.getElementById('ours').src='ours/head/frame-'+s+'.png';
document.getElementById('full').src='legacy/full/frame-'+s+'.png';}
slider.addEventListener('input',show);play.addEventListener('click',()=>{running=!running;play.textContent=running?'Pausar':'Reproduzir'});
setInterval(()=>{if(running){slider.value=(+slider.value+1)%24;show()}},180);
</script></html>
"""
(OUT / "comparison.html").write_text(html, encoding="utf-8")
report = {"status": "completed_diagnostic", "frames_per_model": 24,
          "angle_step_degrees": 15, "action": "action00", "frame": 0,
          "same_camera_lights": True, "legacy": "models/budge-dragon-hd.glb",
          "ours": "work/monster03/v0002-jaw-rotation-floor-test.blend",
          "ours_scope": "isolated_head_only",
          "viewer": "work/monster03/turntable/comparison.html",
          "head_gif": "work/monster03/turntable/head-comparison-360.gif",
          "full_legacy_gif": "work/monster03/turntable/legacy-full-360.gif",
          "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in (gif, full_gif)},
          "caveat": "360 is idle pose; animation defects require separate action/frame comparison."}
(OUT / "comparison-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))

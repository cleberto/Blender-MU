"""Verify that the calibrated visual base still renders identically to HD reference."""
import json
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
base = ROOT / "work" / "monster03" / "turntable" / "legacy" / "head" / "frame-00.png"
calibrated = ROOT / "work" / "monster03" / "turntable" / "calibrated" / "head" / "frame-00.png"
with Image.open(base) as a, Image.open(calibrated) as b:
    if a.size != b.size:
        same = False
        bbox = "size_mismatch"
    else:
        bbox = ImageChops.difference(a.convert("RGBA"), b.convert("RGBA")).getbbox()
        same = bbox is None
report = {"check": "identical_reference_camera_render", "result": "pass" if same else "fail",
          "reference": "work/monster03/turntable/legacy/head/frame-00.png",
          "calibrated": "work/monster03/turntable/calibrated/head/frame-00.png",
          "difference_bbox": bbox, "note": "Same Blender 5.2.2 Eevee turntable script and action00 frame0"}
out = ROOT / "work" / "monster03" / "turntable" / "calibrated-match-report.json"
out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report))
if not same:
    raise SystemExit(1)

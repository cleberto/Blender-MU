"""Measure HD source head coordinates for a controlled neck graft study."""
import json
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
obj = bpy.data.objects["LOD0"]
rows = []
for y0 in (-80, -70, -60, -50, -40, -30, -20, -10, 0, 10):
    points = []
    for v in obj.data.vertices:
        p = obj.matrix_world @ v.co
        if y0 <= p.y < y0 + 10 and abs(p.x) < 35 and 90 < p.z < 180:
            points.append((p.x, p.y, p.z))
    if points:
        rows.append({"y_band": [y0, y0 + 10], "vertices": len(points),
                     "x_bounds": [min(p[0] for p in points), max(p[0] for p in points)],
                     "z_bounds": [min(p[2] for p in points), max(p[2] for p in points)]})
out = ROOT / "work" / "monster03" / "head-source-slices.json"
out.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
print(json.dumps(rows))

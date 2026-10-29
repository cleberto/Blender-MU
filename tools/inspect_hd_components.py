"""Measure connected islands of the inherited HD mesh for calibration."""
import json
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
obj = bpy.data.objects["LOD0"]
n = len(obj.data.vertices)
parent = list(range(n))


def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


for poly in obj.data.polygons:
    indices = list(poly.vertices)
    root = find(indices[0])
    for vertex in indices[1:]:
        parent[find(vertex)] = root
groups = {}
for i in range(n):
    groups.setdefault(find(i), []).append(i)
records = []
for indices in groups.values():
    if len(indices) < 4:
        continue
    points = [obj.matrix_world @ obj.data.vertices[i].co for i in indices]
    records.append({"vertices": len(indices), "bounds": {
        axis: [round(min(p[k] for p in points), 3), round(max(p[k] for p in points), 3)]
        for k, axis in enumerate("xyz")}})
records.sort(key=lambda x: -x["vertices"])
out = {"mesh": "LOD0", "vertex_count": n, "component_count": len(groups),
       "components": records[:80]}
(ROOT / "work" / "monster03" / "hd-components.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"components": len(groups), "largest": records[:8]}))

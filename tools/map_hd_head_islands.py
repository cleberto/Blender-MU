"""Map inherited head mesh islands, skeletal weights and materials."""
import json
from collections import Counter
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
obj = bpy.data.objects["LOD0"]
mesh = obj.data
parent = list(range(len(mesh.vertices)))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


for poly in mesh.polygons:
    indices = list(poly.vertices)
    for i in indices[1:]:
        parent[find(i)] = find(indices[0])

groups = {}
for vertex in mesh.vertices:
    groups.setdefault(find(vertex.index), []).append(vertex.index)
face_counts = Counter(find(poly.vertices[0]) for poly in mesh.polygons)
islands = []
for root, indices in groups.items():
    points = [obj.matrix_world @ mesh.vertices[i].co for i in indices]
    lo = [min(p[k] for p in points) for k in range(3)]
    hi = [max(p[k] for p in points) for k in range(3)]
    if not (lo[1] < -32 and hi[2] > 105 and lo[2] < 175):
        continue
    weights = Counter()
    for i in indices:
        for membership in mesh.vertices[i].groups:
            if membership.weight > 0.25:
                weights[obj.vertex_groups[membership.group].name] += 1
    mat_counts = Counter(poly.material_index for poly in mesh.polygons if find(poly.vertices[0]) == root)
    islands.append({
        "root_vertex": root,
        "vertices": len(indices),
        "faces": face_counts[root],
        "bounds": {axis: [round(lo[k], 2), round(hi[k], 2)] for k, axis in enumerate("xyz")},
        "centroid": [round(sum(p[k] for p in points)/len(points), 2) for k in range(3)],
        "bones": weights.most_common(8),
        "materials": mat_counts.most_common(),
    })
islands.sort(key=lambda row: -row["vertices"])
path = ROOT / "work" / "monster03" / "hd-head-islands.json"
path.write_text(json.dumps(islands, indent=2) + "\n", encoding="utf-8")
print(f"HEAD_ISLAND_MAP={path} islands={len(islands)}")

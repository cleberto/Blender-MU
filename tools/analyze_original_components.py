"""Inventory disconnected mesh islands in the original BMD body."""
import json
from collections import defaultdict
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "original-components.json"
obj = bpy.data.objects["Monster03_original_mesh_0"]
mesh = obj.data
parent = list(range(len(mesh.vertices)))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


for edge in mesh.edges:
    a, b = map(find, edge.vertices)
    parent[b] = a

groups = defaultdict(lambda: {"vertices": set(), "faces": []})
for face in mesh.polygons:
    root = find(face.vertices[0])
    groups[root]["faces"].append(face.index)
    groups[root]["vertices"].update(face.vertices)
result = []
for group in groups.values():
    vertices = [mesh.vertices[i] for i in group["vertices"]]
    positions = [obj.matrix_world @ v.co for v in vertices]
    bones = defaultdict(float)
    for v in vertices:
        for weight in v.groups:
            bones[obj.vertex_groups[weight.group].name] += weight.weight
    result.append({"faces": len(group["faces"]), "vertices": len(vertices),
                   "bounds": {"min": [min(p[k] for p in positions) for k in range(3)],
                              "max": [max(p[k] for p in positions) for k in range(3)]},
                   "bones": sorted(bones.items(), key=lambda x: x[1], reverse=True)[:5]})
result.sort(key=lambda x: x["faces"], reverse=True)
OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print("COMPONENTS_JSON=" + json.dumps(result))

"""Test an intact-island lower jaw on the inherited HD head.

Unlike old thresholded face cuts, this changes only weights on existing complete
mesh islands. It is an experiment, not an approved mouth/rig or final head.
"""
import json
from collections import Counter
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "v0002-hd-jaw-island-test.blend"
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
ordered = []
for root, indices in groups.items():
    points = [obj.matrix_world @ mesh.vertices[i].co for i in indices]
    if min(p.y for p in points) < -32 and max(p.z for p in points) > 105 and min(p.z for p in points) < 175:
        ordered.append((root, indices))
ordered.sort(key=lambda row: -len(row[1]))

jaw_indices = sorted(ordered[5][1] + ordered[7][1])
assert len(jaw_indices) == 148
jaw_faces = [poly.index for poly in mesh.polygons if find(poly.vertices[0]) in (ordered[5][0], ordered[7][0])]
assert len(jaw_faces) == 216
old_bones = Counter()
for index in jaw_indices:
    for membership in mesh.vertices[index].groups:
        old_bones[obj.vertex_groups[membership.group].name] += membership.weight

for group in obj.vertex_groups:
    group.remove(jaw_indices)
obj.vertex_groups["Bone02"].add(jaw_indices, 1.0, "REPLACE")
arm = bpy.data.objects["mu_root"]
for track in arm.animation_data.nla_tracks:
    track.mute = True
arm.animation_data.action = bpy.data.actions["action00"]
bpy.context.scene.frame_set(0)
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
report = {
    "stage": "hd_jaw_island_test", "status": "diagnostic_pending_visual_review",
    "source": "work/monster03/budge-dragon-baseline-v2.blend",
    "output": str(OUT.relative_to(ROOT)).replace("\\", "/"),
    "selection": "Two whole connected islands forming the left and right lower mandible",
    "head_island_ranks": [5, 7], "jaw_vertices": len(jaw_indices),
    "jaw_faces": len(jaw_faces), "old_weight_sums": dict(old_bones),
    "new_weights": {"Bone02": 1.0},
    "geometry_changed": False,
    "materials_uv_changed": False,
    "risk": "May expose an empty mouth or misalign under action; all seven actions require review"
}
(OUT.parent / "hd-jaw-island-test-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("HD_JAW_ISLAND_JSON=" + json.dumps(report))

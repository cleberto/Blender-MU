"""Experiment with a smooth Bone02-to-head transition on intact jaw islands."""
import json
import os
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ["MU_ASSET_OUTPUT"]) if os.environ.get("MU_ASSET_OUTPUT") else ROOT / "work" / "monster03" / "v0002-hd-jaw-gradient-test.blend"
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
count = {"full": 0, "blend": 0, "original": 0}
bone02 = obj.vertex_groups["Bone02"]
head = obj.vertex_groups["Bip01 Head"]
for index in jaw_indices:
    y = (obj.matrix_world @ mesh.vertices[index].co).y
    if y <= -57:
        mix = 1.0
        count["full"] += 1
    elif y >= -42:
        count["original"] += 1
        continue
    else:
        t = (-42 - y) / 15
        mix = t * t * (3 - 2 * t)
        count["blend"] += 1
    # Keep original weights where the jaw joins the cheek/neck; move the front
    # to Bone02 smoothly without selecting or deleting any mesh faces.
    original = {obj.vertex_groups[g.group].name: g.weight for g in mesh.vertices[index].groups}
    for group in obj.vertex_groups:
        if group.name in original:
            group.remove([index])
    for name, weight in original.items():
        remaining = weight * (1 - mix)
        if remaining > 1e-5:
            obj.vertex_groups[name].add([index], remaining, "REPLACE")
    inherited_bone02 = original.get("Bone02", 0)
    bone02.add([index], inherited_bone02 * (1 - mix) + mix, "REPLACE")

# Keep the export contract explicit: at most four skeletal influences per vertex.
# This also cleans a five-influence vertex inherited from the received LOD0.
pruned_vertices = []
for vertex in mesh.vertices:
    memberships = sorted(((g.group, g.weight) for g in vertex.groups),
                         key=lambda row: -row[1])
    if len(memberships) <= 4:
        continue
    keep = memberships[:4]
    total = sum(weight for _, weight in keep)
    for group_id, _ in memberships:
        obj.vertex_groups[group_id].remove([vertex.index])
    for group_id, weight in keep:
        obj.vertex_groups[group_id].add([vertex.index], weight / total, "REPLACE")
    pruned_vertices.append(vertex.index)

arm = bpy.data.objects["mu_root"]
for track in arm.animation_data.nla_tracks:
    track.mute = True
arm.animation_data.action = bpy.data.actions["action00"]
bpy.context.scene.frame_set(0)
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
report = {"stage": "hd_jaw_gradient_test", "status": "diagnostic_pending_visual_review",
          "selected_island_ranks": [5, 7], "vertices": len(jaw_indices),
          "weight_y_full_below": -57, "weight_y_original_above": -42,
          "vertex_counts": count, "geometry_changed": False, "materials_uv_changed": False,
          "vertices_pruned_to_four_influences": pruned_vertices,
          "risk": "Existing jaw seam has no modeled interior and may still tear or intersect"}
(OUT.parent / (OUT.stem + "-build-report.json")).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("HD_JAW_GRADIENT_JSON=" + json.dumps(report))

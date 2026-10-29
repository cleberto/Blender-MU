"""Attempt 04: assign separated lower shell to Bone02, retain a soft hinge."""
import json
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "v0002-attempt04-reweight.blend"
upper = bpy.data.objects["LOD0_upper_plane_test"]
jaw = bpy.data.objects["LOD0_lower_jaw_plane_test"]

head_group = upper.vertex_groups["Bip01 Head"]
bone_group = upper.vertex_groups["Bone02"]
upper_changed = 0
for vertex in upper.data.vertices:
    weight = next((g.weight for g in vertex.groups if g.group == bone_group.index), 0.0)
    if weight:
        old_head = next((g.weight for g in vertex.groups if g.group == head_group.index), 0.0)
        head_group.add([vertex.index], min(1.0, old_head + weight), "REPLACE")
        bone_group.remove([vertex.index])
        upper_changed += 1

head_group = jaw.vertex_groups["Bip01 Head"]
bone_group = jaw.vertex_groups["Bone02"]
for vertex in jaw.data.vertices:
    world_y = (jaw.matrix_world @ vertex.co).y
    bone_weight = max(0.0, min(1.0, (-world_y - 42.0) / 14.0))
    for group in list(vertex.groups):
        jaw.vertex_groups[group.group].remove([vertex.index])
    bone_group.add([vertex.index], max(0.001, bone_weight), "REPLACE")
    head_group.add([vertex.index], max(0.001, 1.0 - bone_weight), "REPLACE")

arm = bpy.data.objects["mu_root"]
for track in arm.animation_data.nla_tracks:
    track.mute = True
arm.animation_data.action = bpy.data.actions["action03"]
bpy.context.scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
report = {"attempt": "v0002-attempt04", "upper_vertices_reassigned_from_Bone02": upper_changed,
          "jaw_vertices_reweighted": len(jaw.data.vertices), "hinge_y_world": -42.0,
          "full_jaw_weight_y_world": -56.0, "status": "needs render review"}
(OUT.parent / "v0002-attempt04-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("ATTEMPT_JSON=" + json.dumps(report))

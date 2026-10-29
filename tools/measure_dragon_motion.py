"""Measure HD dragon jaw motion by original action index in Blender."""
import json
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "motion-report.json"
arm = bpy.data.objects["mu_root"]
mesh = bpy.data.objects["LOD0"]
ad = arm.animation_data
for track in ad.nla_tracks:
    track.mute = True
sample_ids = [v.index for v in mesh.data.vertices if any(
    mesh.vertex_groups[g.group].name == "Bone02" and g.weight >= 0.5 for g in v.groups)]

result = {"jaw_vertices": len(sample_ids), "actions": {}}
for a in (0, 3, 4):
    action = bpy.data.actions[f"action{a:02d}"]
    ad.action = action
    frames = [0, int(action.frame_range[1] // 2), int(action.frame_range[1])]
    samples = []
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = mesh.evaluated_get(depsgraph)
        coords = [evaluated.matrix_world @ evaluated.data.vertices[i].co for i in sample_ids]
        jaw = arm.pose.bones["Bone02"]
        head = arm.pose.bones["Bip01 Head"]
        samples.append({"frame": frame,
                        "jaw_origin": list((arm.matrix_world @ jaw.matrix).translation),
                        "head_origin": list((arm.matrix_world @ head.matrix).translation),
                        "jaw_centroid": [sum(v[k] for v in coords) / len(coords) for k in range(3)],
                        "jaw_rotation": list(jaw.rotation_quaternion)})
    result["actions"][str(a)] = samples
OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print("MOTION_JSON=" + json.dumps(result))

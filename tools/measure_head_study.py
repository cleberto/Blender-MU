"""Sample the anatomical mouth opening in every imported HD action."""
import json
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
trial = "jaw-rotation-floor-test" in bpy.data.filepath
OUT = ROOT / "work" / "monster03" / ("jaw-rotation-floor-action-sweep.json" if trial else "head-study-01-action-sweep.json")
arm = bpy.data.objects["mu_root"]
upper = bpy.data.objects["Study_upper_skull_maxilla"]
jaw = bpy.data.objects["Study_lower_jaw_mandible"]
for obj in (upper, jaw):
    for mod in obj.modifiers:
        if mod.type == "SUBSURF":
            mod.show_viewport = False
for track in arm.animation_data.nla_tracks:
    track.mute = True


def landmark(obj, index):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return evaluated.matrix_world @ evaluated.data.vertices[index].co


result = {"stage": "jaw_rotation_floor_test" if trial else "head_study_01", "method": "World-space landmark distance at center of muzzle tip; not a collision or topology test",
          "landmarks": {"upper_vertex": 7*24+18, "jaw_vertex": 5*24+6}, "actions": {}}
for i in range(7):
    action = bpy.data.actions[f"{'floor_' if trial else ''}action{i:02d}"]
    arm.animation_data.action = action
    frames = list(range(int(action.frame_range[0]), int(action.frame_range[1]) + 1))
    samples = []
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        a = landmark(upper, 7*24+18)
        b = landmark(jaw, 5*24+6)
        samples.append({"frame": frame, "tip_distance": round((a-b).length, 4),
                        "vertical_gap": round(a.z-b.z, 4),
                        "longitudinal_offset": round(a.y-b.y, 4),
                        "bone02_quaternion_x": round(arm.pose.bones["Bone02"].rotation_quaternion.x, 5)})
    result["actions"][f"action{i:02d}"] = {
        "frames": len(frames), "min_tip_distance": min(s["tip_distance"] for s in samples),
        "max_tip_distance": max(s["tip_distance"] for s in samples),
        "min_vertical_gap": min(s["vertical_gap"] for s in samples),
        "max_vertical_gap": max(s["vertical_gap"] for s in samples),
        "samples": samples
    }
OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print("ACTION_SWEEP_JSON=" + json.dumps({k: {key: val for key,val in v.items() if key != "samples"} for k,v in result["actions"].items()}))

"""Test nonnegative Bone02 X rotation while preserving all other action curves.

This changes copies of the seven HD actions only. It does not claim anatomical
correctness; it tests whether the imported animation undershoots the new jaw.
"""
import json
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "v0002-jaw-rotation-floor-test.blend"
arm = bpy.data.objects["mu_root"]
records = []
for i in range(7):
    original = bpy.data.actions[f"action{i:02d}"]
    trial = original.copy()
    trial.name = f"floor_action{i:02d}"
    trial.use_fake_user = True
    altered = 0
    for layer in trial.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    if curve.data_path == 'pose.bones["Bone02"].rotation_quaternion' and curve.array_index == 1:
                        for key in curve.keyframe_points:
                            if key.co.y < 0:
                                altered += 1
                            key.co.y = max(0.0, key.co.y)
                            key.handle_left.y = max(0.0, key.handle_left.y)
                            key.handle_right.y = max(0.0, key.handle_right.y)
                            key.interpolation = "LINEAR"
                        curve.update()
    records.append({"action": original.name, "trial_action": trial.name,
                    "negative_keys_clamped": altered})
for track in arm.animation_data.nla_tracks:
    track.mute = True
arm.animation_data.action = bpy.data.actions["floor_action00"]
bpy.context.scene.frame_set(0)
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
report = {"stage": "jaw_rotation_floor_test", "status": "partial_fix_not_final",
          "clamp": "Bone02 rotation_quaternion X >= 0; key interpolation linear",
          "actions": records, "source": "work/monster03/v0002-head-study-01.blend",
          "no_collision": "tip_crossing_fixed_in_sampled_attack_frames_but_action01_pose_still_displaced"}
(OUT.parent / "jaw-rotation-floor-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("FLOOR_REPORT=" + json.dumps(report))

"""Render consistent full-body side views across every declared action."""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
args = sys.argv[sys.argv.index("--") + 1:]
profile = json.loads((ROOT / args[0]).read_text(encoding="utf-8"))
out = Path(args[1])
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_cavity = True
scene.render.resolution_x = 480
scene.render.resolution_y = 480
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
arm = bpy.data.objects[profile["armature"]]
for track in arm.animation_data.nla_tracks:
    track.mute = True
for name in profile["lod_meshes"][1:]:
    obj = bpy.data.objects.get(name)
    if obj:
        obj.hide_render = True
        obj.hide_set(True)
for name in ("Icosphere", "01_ORIGINAL_BMD"):
    obj = bpy.data.objects.get(name)
    if obj:
        obj.hide_render = True
        obj.hide_set(True)
camera_data = bpy.data.cameras.new("pose_sheet_camera")
camera = bpy.data.objects.new("pose_sheet_camera", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = "ORTHO"
camera_data.ortho_scale = 265
arm.animation_data.action = bpy.data.actions[profile["actions"][0]]
scene.frame_set(0)
root_rest = (arm.matrix_world @ arm.pose.bones["Bip01 Spine"].matrix).translation.copy()
rows = []
for action_name in profile["actions"]:
    action = bpy.data.actions[action_name]
    start = math.floor(action.frame_range[0])
    end = math.ceil(action.frame_range[1])
    frames = (start, (start + end) // 2, end)
    arm.animation_data.action = action
    for slot, frame in enumerate(frames):
        scene.frame_set(frame)
        root = (arm.matrix_world @ arm.pose.bones["Bip01 Spine"].matrix).translation
        target = Vector((0, 3, 84)) + root - root_rest
        camera.location = target + Vector((420, 0, 100))
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        filename = f"{action_name}-{slot}-{frame:02d}.png"
        scene.render.filepath = str(out / filename)
        bpy.ops.render.render(write_still=True)
        rows.append({"action": action_name, "slot": slot, "frame": frame, "image": filename})
(out / "frames.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
print(f"POSE_SHEET_FRAMES={out} count={len(rows)}")

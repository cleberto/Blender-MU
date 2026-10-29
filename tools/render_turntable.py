"""Render deterministic 360-degree Monster03 comparison frames in Blender.

Usage: blender -b <scene.blend> --python tools/render_turntable.py -- legacy|calibrated|ours full|head [steps]
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
variant = args[0] if args else "legacy"
scope = args[1] if len(args) > 1 else "head"
steps = int(args[2]) if len(args) > 2 else 24
destination = args[3] if len(args) > 3 else "turntable"
action_name = args[4] if len(args) > 4 else "action00"
action_frame = int(args[5]) if len(args) > 5 else 0
assert destination in ("turntable", "video-renders", "hd-probe", "body-probe", "eye-probe")
assert variant in ("legacy", "calibrated", "ours", "baseline", "body_pbr")
assert scope in ("head", "full")
OUT = ROOT / "work" / "monster03" / destination / variant / scope
OUT.mkdir(parents=True, exist_ok=True)

scene = bpy.context.scene
arm = bpy.data.objects["mu_root"]
for track in arm.animation_data.nla_tracks:
    track.mute = True
arm.animation_data.action = bpy.data.actions["action00"]
scene.frame_set(0)
head_rest = (arm.matrix_world @ arm.pose.bones["Bip01 Head"].matrix).translation.copy()
arm.animation_data.action = bpy.data.actions[action_name]
scene.frame_set(action_frame)
head_delta = (arm.matrix_world @ arm.pose.bones["Bip01 Head"].matrix).translation - head_rest

is_study = variant == "ours"
for name in ("LOD0", "LOD1", "LOD2", "Icosphere"):
    obj = bpy.data.objects.get(name)
    if obj:
        obj.hide_set(name != "LOD0" or is_study)
        obj.hide_render = name != "LOD0" or is_study
for obj in bpy.data.objects:
    if obj.name.startswith("Study_") or obj.name.startswith("PROBE_"):
        obj.hide_set(not is_study or obj.name.startswith("Study_cheek_fold"))
        obj.hide_render = not is_study or obj.name.startswith("Study_cheek_fold")
if bpy.data.objects.get("01_ORIGINAL_BMD"):
    bpy.data.objects["01_ORIGINAL_BMD"].hide_render = True

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.image_settings.color_mode = "RGBA"
if scene.world is None:
    scene.world = bpy.data.worlds.new("turntable_world")
scene.world.use_nodes = True
scene.world.node_tree.nodes.get("Background").inputs["Color"].default_value = (0.12, 0.12, 0.12, 1)
scene.world.node_tree.nodes.get("Background").inputs["Strength"].default_value = 1.0
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = 3.0

for old in [o for o in bpy.data.objects if o.type == "LIGHT"]:
    bpy.data.objects.remove(old, do_unlink=True)
for name, location, power, size in (
    ("key", (140, -125, 240), 9000, 90),
    ("fill", (-155, -65, 185), 6500, 100),
    ("rim", (75, 145, 230), 9000, 95),
):
    light_data = bpy.data.lights.new(name, "AREA")
    light_data.energy = power
    light_data.shape = "DISK"
    light_data.size = size
    light = bpy.data.objects.new(name, light_data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (Vector((0, -25, 90)) - light.location).to_track_quat("-Z", "Y").to_euler()

camera_data = bpy.data.cameras.new("turntable_camera")
camera = bpy.data.objects.new("turntable_camera", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = "ORTHO"
camera_data.lens = 50
target = (Vector((0, -47, 136)) if scope == "head" else Vector((0, 3, 84))) + head_delta
camera_data.ortho_scale = 90 if scope == "head" else 265
radius = 240 if scope == "head" else 420
elevation = 22 if scope == "head" else 100

for index in range(steps):
    angle = index * math.tau / steps
    camera.location = target + Vector((radius * math.cos(angle), -radius * math.sin(angle), elevation))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT / f"frame-{index:02d}.png")
    bpy.ops.render.render(write_still=True)

notes = ("Same camera/light protocol. Body PBR study changes copied scalar material controls only."
         if variant == "body_pbr" else
         "Same camera/light protocol. Ours is an isolated graybox head, not a full-dragon candidate."
         if variant == "ours" else
         "Same camera/light protocol; no source mesh or material edits were applied by this renderer.")
report = {"variant": variant, "scope": scope, "steps": steps,
          "source_scene": bpy.data.filepath, "render_engine": scene.render.engine,
          "action": action_name, "frame": action_frame,
          "target": list(target), "ortho_scale": camera_data.ortho_scale,
          "angles_degrees": [round(i*360/steps, 3) for i in range(steps)],
          "notes": notes}
(OUT / "render-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("TURNTABLE_JSON=" + json.dumps(report))

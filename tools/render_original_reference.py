"""Render original BMD head, using the same view/crop as HD diagnostics."""
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "original-renders"
OUT.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
bpy.data.collections["00_ORIGINAL_BMD_reference"].hide_viewport = False
bpy.data.collections["00_ORIGINAL_BMD_reference"].hide_render = False
bpy.data.collections["01_HD_GLB_candidate_v0001"].hide_viewport = True
bpy.data.collections["01_HD_GLB_candidate_v0001"].hide_render = True
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.light = "STUDIO"
scene.display.shading.show_cavity = True
arm = bpy.data.objects["Monster03_original_Armature"]
camera_data = bpy.data.cameras.new("original_reference_camera")
camera = bpy.data.objects.new("original_reference_camera", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = "ORTHO"
camera_data.ortho_scale = 85

for action, frame in ((0, 0), (3, 0), (3, 3), (4, 0), (4, 3)):
    arm.animation_data.action = bpy.data.actions[f"action_{action}"]
    scene.frame_set(frame)
    head = (arm.matrix_world @ arm.pose.bones["Bip01 Head"].matrix).translation
    for view, delta in (("side", Vector((170, -10, 5))), ("front", Vector((0, -170, 5)))):
        target = head + Vector((0, -15, 2))
        camera.location = target + delta
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(OUT / f"action{action:02d}-frame{frame:02d}-{view}.png")
        bpy.ops.render.render(write_still=True)

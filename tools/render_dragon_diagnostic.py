"""Render comparable close-up jaw frames from the untouched HD candidate."""
from pathlib import Path
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
variant = ("cheek-hinge-study" if "cheek-hinge-study" in bpy.data.filepath else
           "jaw-rotation-floor-test" if "jaw-rotation-floor-test" in bpy.data.filepath else
           "head-study-02" if "head-study-02" in bpy.data.filepath else
           "head-graft-probe" if "head-graft-probe" in bpy.data.filepath else
           "head-study-01" if "head-study-01" in bpy.data.filepath else
           "attempt04" if "attempt04" in bpy.data.filepath else
           "attempt03" if bpy.data.objects.get("LOD0_lower_jaw_plane_test") else
           "attempt02" if bpy.data.objects.get("LOD0_lower_jaw_test") else "baseline")
if "--" in sys.argv:
    override = sys.argv[sys.argv.index("--") + 1:]
    if override:
        variant = override[0]
OUT = ROOT / "work" / "monster03" / "diagnostic-renders" / variant
OUT.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
arm = bpy.data.objects["mu_root"]
ad = arm.animation_data
for track in ad.nla_tracks:
    track.mute = True
camera_data = bpy.data.cameras.new("diagnostic_camera")
camera = bpy.data.objects.new("diagnostic_camera", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = "ORTHO"
camera_data.ortho_scale = 85

for action_index, frame in [(0, 0), (0, 5), (1, 10), (1, 25), (1, 26), (3, 0), (3, 2), (3, 3), (4, 0), (4, 3)]:
    ad.action = bpy.data.actions[f"{'floor_' if variant in ('jaw-rotation-floor-test', 'cheek-hinge-study') else ''}action{action_index:02d}"]
    scene.frame_set(frame)
    head = (arm.matrix_world @ arm.pose.bones["Bip01 Head"].matrix).translation
    for view, delta in (("side", Vector((170, -10, 5))), ("front", Vector((0, -170, 5)))):
        target = head + Vector((0, -15, 2))
        camera.location = target + delta
        camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(OUT / f"action{action_index:02d}-frame{frame:02d}-{view}.png")
        bpy.ops.render.render(write_still=True)

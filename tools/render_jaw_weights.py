"""Render Bone02-weighted triangles in red for segmentation review."""
import bpy
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.light = "STUDIO"
scene.display.shading.show_cavity = True
o = bpy.data.objects["LOD0"]
g = o.vertex_groups["Bone02"].index
w = {v.index: max([x.weight for x in v.groups if x.group == g] or [0.0]) for v in o.data.vertices}
mat = bpy.data.materials.new("Bone02_weight_high_red")
mat.diffuse_color = (1.0, 0.02, 0.02, 1.0)
o.data.materials.append(mat)
idx = len(o.data.materials) - 1
for p in o.data.polygons:
    center = o.matrix_world @ p.center
    if center.y < -42 and center.z < 119:
        p.material_index = idx
arm = bpy.data.objects["mu_root"]
for track in arm.animation_data.nla_tracks:
    track.mute = True
arm.animation_data.action = bpy.data.actions["action00"]
scene.frame_set(0)
head = (arm.matrix_world @ arm.pose.bones["Bip01 Head"].matrix).translation
camera_data = bpy.data.cameras.new("jaw_mask_camera")
camera = bpy.data.objects.new("jaw_mask_camera", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.type = "ORTHO"
camera_data.ortho_scale = 70
target = head + Vector((0, -17, -1))
camera.location = target + Vector((170, -10, 3))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
scene.render.filepath = str(ROOT / "work" / "monster03" / "jaw-spatial-mask.png")
bpy.ops.render.render(write_still=True)

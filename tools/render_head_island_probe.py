"""Color connected head islands to locate an intact movable jaw shell."""
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "head-island-probe"
OUT.mkdir(parents=True, exist_ok=True)
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
for v in mesh.vertices:
    groups.setdefault(find(v.index), []).append(v.index)
ordered = []
for root, indices in groups.items():
    pts = [obj.matrix_world @ mesh.vertices[i].co for i in indices]
    if min(p.y for p in pts) < -32 and max(p.z for p in pts) > 105 and min(p.z for p in pts) < 175:
        ordered.append((root, len(indices)))
ordered.sort(key=lambda row: -row[1])
rank = {root: index for index, (root, _) in enumerate(ordered)}

copy = obj.copy()
copy.data = obj.data.copy()
copy.name = "PROBE_head_islands"
bpy.context.scene.collection.objects.link(copy)
obj.hide_set(True)
obj.hide_render = True
for name in ("LOD1", "LOD2", "Icosphere"):
    other = bpy.data.objects.get(name)
    if other:
        other.hide_set(True)
        other.hide_render = True

colors = {2: (0.9, 0.08, 0.05, 1), 3: (1.0, 0.44, 0.06, 1),
          4: (0.93, 0.9, 0.04, 1), 5: (0.1, 0.3, 0.95, 1),
          7: (0.05, 0.85, 0.23, 1)}
copy.data.materials.clear()
for color in [(0.28, 0.29, 0.3, 1)] + list(colors.values()):
    mat = bpy.data.materials.new("island_probe")
    mat.diffuse_color = color
    copy.data.materials.append(mat)
lookup = {key: index + 1 for index, key in enumerate(colors)}
for poly in copy.data.polygons:
    poly.material_index = lookup.get(rank.get(find(poly.vertices[0])), 0)

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "MATERIAL"
scene.display.shading.show_shadows = True
scene.render.resolution_x = scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
arm = bpy.data.objects["mu_root"]
for track in arm.animation_data.nla_tracks:
    track.mute = True
arm.animation_data.action = bpy.data.actions["action00"]
scene.frame_set(0)
cam_data = bpy.data.cameras.new("probe_camera")
cam = bpy.data.objects.new("probe_camera", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.type = "ORTHO"
cam_data.ortho_scale = 90
target = Vector((0, -47, 136))
for angle in (0, 45, 90, 180):
    theta = math.radians(angle)
    cam.location = target + Vector((240 * math.cos(theta), -240 * math.sin(theta), 22))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT / f"islands-{angle:03d}.png")
    bpy.ops.render.render(write_still=True)
print(f"ISLAND_PROBE={OUT}")

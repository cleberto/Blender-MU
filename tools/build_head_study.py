"""Create a sculptable Monster03 head study with truly separate jaw surfaces.

It is deliberately a graybox anatomy/rig test. It does not replace the HD model.
Run against work/monster03/budge-dragon-baseline-v2.blend.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "v0002-head-study-01.blend"
arm = bpy.data.objects["mu_root"]
source = bpy.data.objects["LOD0"]
to_local = source.matrix_world.inverted()
collection = bpy.data.collections.new("02_HEAD_REBUILD_STUDY_01")
bpy.context.scene.collection.children.link(collection)


def material(name, rgb):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1.0)
    mat.use_nodes = True
    mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (*rgb, 1.0)
    mat.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = 0.68
    return mat


skin = material("Study_skin_copper_red", (0.34, 0.065, 0.04))
mouth = material("Study_mouth_dark_burgundy", (0.045, 0.006, 0.012))
ivory = material("Study_teeth_ivory", (0.82, 0.72, 0.54))
eye = material("Study_eye_amber", (0.7, 0.36, 0.08))


def make_mesh(name, world_vertices, faces, mat, bone, face_materials=None, extra_material=None):
    vertices = [tuple(to_local @ Vector(v)) for v in world_vertices]
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.matrix_world = source.matrix_world.copy()
    mesh.materials.append(mat)
    if extra_material:
        mesh.materials.append(extra_material)
    for index, face in enumerate(mesh.polygons):
        face.use_smooth = True
        if face_materials:
            face.material_index = face_materials[index]
    group = obj.vertex_groups.new(name=bone)
    group.add(list(range(len(vertices))), 1.0, "REPLACE")
    mod = obj.modifiers.new("HD_skeleton", "ARMATURE")
    mod.object = arm
    return obj


def loft(name, sections, bone, interior_side):
    ring_size = 24
    vertices = []
    faces = []
    face_mats = []
    for y, rx, z_top, z_bottom in sections:
        mid = (z_top + z_bottom) / 2
        rz = (z_top - z_bottom) / 2
        for i in range(ring_size):
            theta = i * 2 * math.pi / ring_size
            x = rx * math.cos(theta)
            z = mid + rz * math.sin(theta)
            # Slightly square muzzle and raised supraorbital ridges.
            x *= 1 + 0.08 * math.cos(2 * theta)
            vertices.append((x, y, z))
    for ring in range(len(sections) - 1):
        for i in range(ring_size):
            j = (i + 1) % ring_size
            faces.append((ring * ring_size + i, ring * ring_size + j,
                          (ring + 1) * ring_size + j, (ring + 1) * ring_size + i))
            sin_mid = math.sin((i + 0.5) * 2 * math.pi / ring_size)
            face_mats.append(1 if sin_mid * interior_side > 0.68 else 0)
    faces.append(tuple(reversed(range(ring_size))))
    face_mats.append(0)
    start = (len(sections) - 1) * ring_size
    faces.append(tuple(start + i for i in range(ring_size)))
    face_mats.append(0)
    obj = make_mesh(name, vertices, faces, skin, bone, face_mats, mouth)
    sub = obj.modifiers.new("Study_smooth_quads", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 2
    return obj


upper_sections = [
    (-24, 11, 154, 128), (-32, 15, 158, 125), (-43, 15, 154, 123),
    (-53, 14, 146, 122), (-63, 12, 136, 120), (-72, 10, 129, 119),
    (-77, 7, 125, 119), (-79, 2, 121, 119)
]
jaw_sections = [
    (-42, 7, 122, 115), (-49, 11, 120, 111), (-59, 11.5, 118, 108),
    (-69, 10, 118, 109), (-76, 7, 119, 113), (-79, 2, 119, 116)
]
upper = loft("Study_upper_skull_maxilla", upper_sections, "Bip01 Head", -1)
jaw = loft("Study_lower_jaw_mandible", jaw_sections, "Bone02", +1)


def ellipsoid(name, center, radii, mat, bone, segments=16, rings=8):
    verts = []
    faces = []
    for r in range(rings + 1):
        phi = math.pi * r / rings
        for s in range(segments):
            theta = 2 * math.pi * s / segments
            verts.append((center[0] + radii[0] * math.sin(phi) * math.cos(theta),
                          center[1] + radii[1] * math.sin(phi) * math.sin(theta),
                          center[2] + radii[2] * math.cos(phi)))
    for r in range(rings):
        for s in range(segments):
            n = (s + 1) % segments
            faces.append((r * segments + s, r * segments + n,
                          (r + 1) * segments + n, (r + 1) * segments + s))
    return make_mesh(name, verts, faces, mat, bone)


for side in (-1, 1):
    ellipsoid(f"Study_eye_{side}", (side * 13.7, -45, 143), (2.4, 3.8, 2.6), eye, "Bip01 Head")
    ellipsoid(f"Study_brow_{side}", (side * 13.5, -43, 147), (3.5, 5.5, 2), skin, "Bip01 Head")
    ellipsoid(f"Study_nostril_{side}", (side * 5.3, -75.2, 124), (1.4, 1.1, 0.6), mouth, "Bip01 Head")


def cone(name, x, y, z_base, length, radius, direction, bone):
    n = 10
    vertices = [(x + radius * math.cos(i * 2 * math.pi / n),
                 y + radius * math.sin(i * 2 * math.pi / n), z_base) for i in range(n)]
    vertices.append((x, y, z_base + direction * length))
    faces = [(i, (i + 1) % n, n) for i in range(n)]
    faces.append(tuple(reversed(range(n))))
    return make_mesh(name, vertices, faces, ivory, bone)


for side in (-1, 1):
    for idx, y in enumerate((-52, -61, -70)):
        x = side * (10.8 if y == -52 else 9.2 if y == -61 else 7.4)
        cone(f"Study_upper_tooth_{side}_{idx}", x, y, 121.5, 3.5 if idx == 0 else 2.2,
             0.9, -1, "Bip01 Head")
        cone(f"Study_lower_tooth_{side}_{idx}", x * 0.87, y, 117.0, 2.4, 0.8, +1, "Bone02")

for obj in (upper, jaw):
    obj["study_stage"] = "anatomy_and_rig_only"
    obj["not_final"] = True
for name in ("LOD0", "LOD1", "LOD2", "Icosphere"):
    obj = bpy.data.objects.get(name)
    if obj:
        obj.hide_set(True)
        obj.hide_render = True
for track in arm.animation_data.nla_tracks:
    track.mute = True
arm.animation_data.action = bpy.data.actions["action00"]
bpy.context.scene.frame_set(0)
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
report = {"stage": "head_study_01", "status": "rejected_as_final_rig",
          "objects": [o.name for o in collection.objects],
          "source": "BMD jaw bounds + HD head bounds", "jaw_bone": "Bone02",
          "upper_bone": "Bip01 Head", "roundtrip_export": "pending",
          "body_graft": "pending", "uv_bake": "pending", "lod": "pending",
          "all_action_sweep": "work/monster03/head-study-01-action-sweep.json",
          "all_action_result": "fail_muzzle_tip_crossing_in_intermediate_frames"}
(OUT.parent / "head-study-01-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("HEAD_STUDY_JSON=" + json.dumps(report))

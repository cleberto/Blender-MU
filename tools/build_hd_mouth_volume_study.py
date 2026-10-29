"""Add anatomical mouth-volume test geometry to the inherited HD dragon.

Creates a palate/cavity, tongue, gums and teeth bound to the existing rig.
This is a sculpt/rig study requiring full visual review before selection.
"""
import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ["MU_ASSET_OUTPUT"]) if os.environ.get("MU_ASSET_OUTPUT") else ROOT / "work" / "monster03" / "v0002-hd-mouth-volume-study-02.blend"
source = bpy.data.objects["LOD0"]
arm = bpy.data.objects["mu_root"]
to_local = source.matrix_world.inverted()
collection = bpy.data.collections.new("V0002_MOUTH_VOLUME_STUDY")
bpy.context.scene.collection.children.link(collection)


def material(name, base, roughness):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*base, 1)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = (*base, 1)
    node.inputs["Roughness"].default_value = roughness
    return mat


cavity_mat = material("M03_Mouth_Cavity_Burgundy", (0.055, 0.009, 0.014), 0.72)
gum_mat = material("M03_Gum_Deep_Rose", (0.22, 0.047, 0.056), 0.51)
tongue_mat = material("M03_Tongue_Dusky_Rose", (0.30, 0.068, 0.074), 0.47)
tooth_mat = material("M03_Tooth_Warm_Ivory", (0.78, 0.68, 0.52), 0.34)


def mesh_object(name, points, faces, mat, bone):
    data = bpy.data.meshes.new(name + "_mesh")
    data.from_pydata([tuple(to_local @ Vector(p)) for p in points], [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.matrix_world = source.matrix_world.copy()
    data.materials.append(mat)
    for face in data.polygons:
        face.use_smooth = True
    group = obj.vertex_groups.new(name=bone)
    group.add(list(range(len(points))), 1.0, "REPLACE")
    modifier = obj.modifiers.new("HD_skeleton", "ARMATURE")
    modifier.object = arm
    obj["study_stage"] = "anatomy_and_material_probe"
    return obj


def tube(name, sections, mat, bone, sides=16):
    points, faces = [], []
    for y, width, z, height in sections:
        for i in range(sides):
            angle = 2 * math.pi * i / sides
            points.append((width * math.cos(angle), y, z + height * math.sin(angle)))
    for ring in range(len(sections) - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((ring * sides + i, ring * sides + j,
                          (ring + 1) * sides + j, (ring + 1) * sides + i))
    faces.append(tuple(reversed(range(sides))))
    last = (len(sections) - 1) * sides
    faces.append(tuple(last + i for i in range(sides)))
    return mesh_object(name, points, faces, mat, bone)


def fang(name, x, y, z, length, direction, radius, bone):
    sides = 10
    points = []
    for step, (r, advance) in enumerate(((radius, 0), (radius * 0.70, 0.38),
                                         (radius * 0.35, 0.75), (0.03, 1.0))):
        for i in range(sides):
            angle = i * math.tau / sides
            bend = (step / 3) ** 2 * 0.35
            points.append((x + r * math.cos(angle), y + r * math.sin(angle) - bend,
                           z + direction * length * advance))
    faces = []
    for ring in range(3):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((ring * sides + i, ring * sides + j,
                          (ring + 1) * sides + j, (ring + 1) * sides + i))
    faces.append(tuple(reversed(range(sides))))
    return mesh_object(name, points, faces, tooth_mat, bone)


cavity = tube("MouthInterior_Cavity", [
    (-76, 1.5, 117.1, 0.3), (-73, 4.6, 117.6, 1.2),
    (-66, 6.4, 118.2, 1.9), (-58, 8.0, 119.0, 2.0),
    (-50, 9.2, 119.5, 2.0), (-44, 7.2, 120.2, 1.6),
    (-40, 2.4, 121.0, 0.3)
], cavity_mat, "Bip01 Head")
tongue = tube("MouthInterior_Tongue", [
    (-72, 1.0, 116.8, 0.25), (-68, 3.4, 117.2, 0.6),
    (-60, 5.8, 118.0, 0.8), (-52, 6.2, 118.8, 0.7),
    (-46, 2.8, 119.7, 0.4)
], tongue_mat, "Bone02")
for side in (-1, 1):
    for index, (y, x, upper_z, lower_z, upper_len, lower_len) in enumerate((
        (-70, 6.0, 121.6, 116.5, 2.6, 2.2),
        (-61, 9.2, 122.2, 118.7, 2.4, 2.0),
        (-52, 11.7, 122.0, 120.9, 1.8, 1.7),
    )):
        fang(f"M03_Upper_Fang_{side}_{index}", side * x, y, upper_z,
             upper_len, -1, 0.9 if index == 0 else 0.65, "Bip01 Head")
        fang(f"M03_Lower_Fang_{side}_{index}", side * (x - 0.8), y, lower_z,
             lower_len, +1, 0.7 if index == 0 else 0.55, "Bone02")

for track in arm.animation_data.nla_tracks:
    track.mute = True
arm.animation_data.action = bpy.data.actions["action00"]
bpy.context.scene.frame_set(0)
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
report = {"stage": "hd_mouth_volume_study", "status": "diagnostic_pending_visual_review",
          "scene": str(OUT.relative_to(ROOT)).replace("\\", "/"),
          "objects": [obj.name for obj in collection.objects],
          "source_head_and_body_geometry_changed": False,
          "jaw_island_weights_inherited_from": "tools/build_hd_jaw_gradient_test.py",
          "limitations": ["Cavity and fangs are early anatomy guides, not approved retopology or final UV/PBR.",
                          "Lip border and volumetric cheek tissue remain unresolved.",
                          "Every action frame and game camera must be visually reviewed."]}
(OUT.parent / (OUT.stem + "-mouth-report.json")).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("MOUTH_VOLUME_JSON=" + json.dumps(report))

"""Add a small deforming cheek web behind the mouth opening.

Anatomy/weight study only. This does not solve the skull-neck graft or surface.
"""
import json
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "v0002-cheek-hinge-study.blend"
arm = bpy.data.objects["mu_root"]
source = bpy.data.objects["Study_upper_skull_maxilla"]
collection = bpy.data.collections.new("03_CHEEK_HINGE_STUDY")
bpy.context.scene.collection.children.link(collection)
mat = bpy.data.materials.new("Study_cheek_fold_copper")
mat.diffuse_color = (0.23, 0.038, 0.034, 1)
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = mat.diffuse_color
mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.76

results = []
for side in (-1, 1):
    # A narrow elastic cheek band: skull edge, soft middle, jaw branch.
    # Ends before the anterior mouth so attacks keep a readable opening.
    top = [(side*13.5, -41, 133), (side*13.5, -46, 128), (side*11.5, -52, 123)]
    bottom = [(side*8.5, -41, 117), (side*11.0, -46, 113), (side*11.0, -52, 112)]
    verts_world = []
    weights = []
    for a, b in zip(top, bottom):
        for t in (0.0, 0.5, 1.0):
            verts_world.append(tuple((1-t)*a[k] + t*b[k] for k in range(3)))
            weights.append(t)
    faces = []
    for j in range(2):
        for k in range(2):
            u = j*3+k
            faces.append((u, u+1, u+4, u+3) if side == 1 else (u+3, u+4, u+1, u))
    mesh = bpy.data.meshes.new(f"Cheek_fold_{side}_mesh")
    mesh.from_pydata([tuple(source.matrix_world.inverted() @ Vector(v)) for v in verts_world], [], faces)
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(f"Study_cheek_fold_{side}", mesh)
    collection.objects.link(obj)
    obj.matrix_world = source.matrix_world.copy()
    head = obj.vertex_groups.new(name="Bip01 Head")
    jaw = obj.vertex_groups.new(name="Bone02")
    for index, weight in enumerate(weights):
        if weight < 1:
            head.add([index], 1-weight, "REPLACE")
        if weight > 0:
            jaw.add([index], weight, "REPLACE")
    modifier = obj.modifiers.new("HD_skeleton", "ARMATURE")
    modifier.object = arm
    thick = obj.modifiers.new("Cheek_web_thickness", "SOLIDIFY")
    thick.thickness = 0.35
    results.append({"object": obj.name, "vertices": len(mesh.vertices), "faces": len(mesh.polygons)})

OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
report = {"stage": "cheek_hinge_study", "status": "rejected",
          "source": "work/monster03/v0002-jaw-rotation-floor-test.blend",
          "objects": results, "bones": ["Bip01 Head", "Bone02"],
          "weight_rows": [0, 0.5, 1], "no_neck_graft": True,
          "review": "Flat weighted cheek bands deform as visible cardboard flaps and fail to hide the hinge in action01 frame25. Require volumetric cheek/temporal anatomy with controlled topology."}
(OUT.parent / "cheek-hinge-study-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("CHEEK_STUDY_JSON=" + json.dumps(report))

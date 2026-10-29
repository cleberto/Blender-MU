"""Attempt 02: separate Bone02-driven lower snout; preserve all original assets.

This is an experimental topology test, not an approved dragon.
"""
import json
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "v0002-attempt02-jaw-split.blend"
mesh = bpy.data.objects["LOD0"]
group = mesh.vertex_groups["Bone02"].index
weights = {v.index: max([a.weight for a in v.groups if a.group == group] or [0])
           for v in mesh.data.vertices}
selected = [p.index for p in mesh.data.polygons
            if sum(weights[i] for i in p.vertices) / len(p.vertices) >= 0.2]
if not 150 <= len(selected) <= 400:
    raise RuntimeError(f"Unexpected lower-jaw face count: {len(selected)}")

bpy.ops.object.select_all(action="DESELECT")
mesh.select_set(True)
bpy.context.view_layer.objects.active = mesh
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="DESELECT")
bpy.ops.object.mode_set(mode="OBJECT")
for p in mesh.data.polygons:
    p.select = p.index in selected
before = set(bpy.data.objects)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.separate(type="SELECTED")
bpy.ops.object.mode_set(mode="OBJECT")
new_objects = [o for o in set(bpy.data.objects) - before if o.type == "MESH"]
if len(new_objects) != 1:
    raise RuntimeError(f"Expected exactly one separated jaw object; got {len(new_objects)}")
jaw = new_objects[0]
if len(mesh.data.polygons) + len(jaw.data.polygons) != 6002 or not 150 <= len(jaw.data.polygons) <= 400:
    raise RuntimeError(f"Invalid split: {len(mesh.data.polygons)} + {len(jaw.data.polygons)} faces")
mesh.name = "LOD0_upper_open_test"
jaw.name = "LOD0_lower_jaw_test"
interior = bpy.data.materials.new("MouthInterior_test_darkred")
interior.diffuse_color = (0.08, 0.006, 0.006, 1)
interior.use_nodes = True
interior.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = interior.diffuse_color
jaw.data.materials.append(interior)
solid = jaw.modifiers.new("TEST_jaw_inner_surface", "SOLIDIFY")
solid.thickness = 1.0
solid.offset = -1
solid.material_offset_rim = 1
solid.material_offset = 1

arm = bpy.data.objects["mu_root"]
for track in arm.animation_data.nla_tracks:
    track.mute = True
arm.animation_data.action = bpy.data.actions["action03"]
bpy.context.scene.frame_set(0)
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
report = {"attempt": "v0002-attempt02", "method": "split faces with mean Bone02 weight >= 0.2",
          "selected_faces": len(selected), "upper_faces": len(mesh.data.polygons),
          "jaw_faces": len(jaw.data.polygons), "jaw_modifier": "solidify 1 MU unit",
          "source_unchanged": True, "status": "needs visual and motion review"}
(OUT.parent / "v0002-attempt02-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("ATTEMPT_JSON=" + json.dumps(report))

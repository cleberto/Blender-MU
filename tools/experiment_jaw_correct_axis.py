"""Correct the earlier jaw-plane axis error and test a true z lip cut.

Exploratory only: the face mask, cap geometry and animation must pass review.
"""
import json
from pathlib import Path

import bmesh
import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "v0002-attempt05-correct-axis-jaw.blend"
obj = bpy.data.objects["LOD0"]
bm = bmesh.new()
bm.from_mesh(obj.data)
faces = [face for face in bm.faces if
         (lambda c: c.y < -38 and abs(c.x) < 23 and 102 < c.z < 140)(obj.matrix_world @ face.calc_center_median())]
geometry = set(faces)
for face in faces:
    geometry.update(face.edges)
    geometry.update(face.verts)
cut = bmesh.ops.bisect_plane(bm, geom=list(geometry), dist=0.0001,
                             plane_co=(0, 0, 120), plane_no=(0, 0, 1),
                             clear_inner=False, clear_outer=False)
bm.to_mesh(obj.data)
bm.free()
obj.data.update()

bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.context.view_layer.objects.active = obj
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="DESELECT")
bpy.ops.object.mode_set(mode="OBJECT")
selected = []
for poly in obj.data.polygons:
    c = obj.matrix_world @ poly.center
    if c.y < -43 and abs(c.x) < 19 and 104 < c.z < 120:
        poly.select = True
        selected.append(poly.index)
before = set(bpy.data.objects)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.separate(type="SELECTED")
bpy.ops.object.mode_set(mode="OBJECT")
new_objects = [o for o in set(bpy.data.objects) - before if o.type == "MESH"]
assert len(new_objects) == 1
jaw = new_objects[0]
assert 150 < len(jaw.data.polygons) < 1000, len(jaw.data.polygons)
indices = list(range(len(jaw.data.vertices)))
for group in jaw.vertex_groups:
    group.remove(indices)
jaw.vertex_groups["Bone02"].add(indices, 1.0, "REPLACE")
obj.name = "LOD0_upper_correct_axis_test"
jaw.name = "LOD0_lower_correct_axis_test"
arm = bpy.data.objects["mu_root"]
for track in arm.animation_data.nla_tracks:
    track.mute = True
arm.animation_data.action = bpy.data.actions["action00"]
bpy.context.scene.frame_set(0)
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
report = {"attempt": "v0002-attempt05", "plane_point": [0, 0, 120],
          "plane_normal": [0, 0, 1], "bisect_faces": len(faces),
          "bisect_geom_result": len(cut.get("geom", [])),
          "selected_faces": len(selected), "upper_faces": len(obj.data.polygons),
          "jaw_faces": len(jaw.data.polygons), "jaw_vertices": len(indices),
          "jaw_bone": "Bone02", "status": "diagnostic_pending_visual_review"}
(OUT.parent / "v0002-attempt05-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("ATTEMPT05_JSON=" + json.dumps(report))

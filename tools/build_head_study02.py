"""Second neck interface study; destructive operations only on copied geometry."""
import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "v0002-head-study-02.blend"
upper = bpy.data.objects["Study_upper_skull_maxilla"]
source = bpy.data.objects["LOD0"]

# Shorten the rear of the study skull to the base of the inherited head.
# The first two loft rings are the only altered ones; all other trial parameters
# remain recorded in tools/build_head_study.py.
upper_params = ((-38, 15, 157, 126), (-41, 15, 155, 124))
for ring_index, (y, rx, z_top, z_bottom) in enumerate(upper_params):
    for i in range(24):
        v = upper.data.vertices[ring_index * 24 + i]
        world = upper.matrix_world @ v.co
        import math
        theta = i * 2 * math.pi / 24
        world.x = rx * math.cos(theta) * (1 + 0.08 * math.cos(2 * theta))
        world.y = y
        world.z = (z_top + z_bottom) / 2 + (z_top - z_bottom) / 2 * math.sin(theta)
        v.co = upper.matrix_world.inverted() @ world
upper.data.update()

body = source.copy()
body.data = source.data.copy()
body.name = "Study02_body_with_head_cut"
bpy.context.scene.collection.objects.link(body)
body.hide_set(False)
body.hide_render = False
bm = bmesh.new()
bm.from_mesh(body.data)
before = len(bm.faces)
remove = []
for face in bm.faces:
    center = sum((body.matrix_world @ v.co for v in face.verts), Vector((0, 0, 0))) / len(face.verts)
    if center.y < -42 and abs(center.x) < 20 and 105 < center.z < 158:
        remove.append(face)
bmesh.ops.delete(bm, geom=remove, context="FACES")
after = len(bm.faces)
boundary = sum(1 for edge in bm.edges if edge.is_boundary)
bm.to_mesh(body.data)
bm.free()
body.data.update()
source.hide_set(True)
source.hide_render = True

OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
report = {"stage": "head_study_02", "status": "diagnostic_not_final",
          "skull_back_rings": upper_params, "cut": {"y_less_than": -42,
          "abs_x_less_than": 20, "z_between": [105, 158]},
          "body_faces_before": before, "body_faces_removed": before-after,
          "body_boundary_edges": boundary, "source_boundary_edges": 3062,
          "boundary_note": "Source LOD0 is already non-manifold with split shells/UV seams; compare the local neck seam visually and by region, not global count.",
          "visual_review": "rejected_jagged_neck_seam_and_exposed_horn_root"}
(OUT.parent / "head-study-02-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("HEAD_STUDY_02_JSON=" + json.dumps(report))

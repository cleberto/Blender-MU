"""Destructive-on-copy mesh graft probe; preserves the original GLB and baseline.

This is a diagnostic study, not a production body/neck attachment.
"""
import json
from pathlib import Path

import bmesh
import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "v0002-head-graft-probe.blend"
source = bpy.data.objects["LOD0"]
body = source.copy()
body.data = source.data.copy()
body.name = "PROBE_body_head_cut"
bpy.context.scene.collection.objects.link(body)
body.hide_set(False)
body.hide_render = False

bm = bmesh.new()
bm.from_mesh(body.data)
faces_before = len(bm.faces)
remove = []
for face in bm.faces:
    center = sum((body.matrix_world @ v.co for v in face.verts),
                 __import__("mathutils").Vector((0, 0, 0))) / len(face.verts)
    if center.y < -31 and abs(center.x) < 20 and 106 < center.z < 166:
        remove.append(face)
bmesh.ops.delete(bm, geom=remove, context="FACES")
remaining = len(bm.faces)
open_edges = sum(1 for edge in bm.edges if edge.is_boundary)
bm.to_mesh(body.data)
bm.free()
body.data.update()
body["study_stage"] = "graft_probe_only"
source.hide_set(True)
source.hide_render = True

OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
report = {"stage": "head_graft_probe", "status": "diagnostic_not_final",
          "input": "work/monster03/v0002-head-study-01.blend",
          "cut_world_bounds": {"y_less_than": -31, "abs_x_less_than": 20,
                               "z_greater_than": 106, "z_less_than": 166},
          "faces_before": faces_before, "faces_removed": faces_before - remaining,
          "open_boundary_edges": open_edges, "source_open_boundary_edges": 3062,
          "boundary_note": "Source LOD0 is already non-manifold with split shells/UV seams; total edge count alone does not establish graft quality. Visual seam failure is decisive.",
          "topology_acceptance": "rejected_jagged_open_neck_and_detached_horn"}
(OUT.parent / "head-graft-probe-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("GRAFT_PROBE_JSON=" + json.dumps(report))

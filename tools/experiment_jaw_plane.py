"""Attempt 03: cut a controlled lip plane before separating the lower jaw."""
import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "v0002-attempt03-jaw-plane.blend"
obj = bpy.data.objects["LOD0"]
bm = bmesh.new()
bm.from_mesh(obj.data)
faces = [f for f in bm.faces if
         (lambda c: c.y < -40 and abs(c.x) < 23 and 102 < c.z < 140)(obj.matrix_world @ f.calc_center_median())]
geom = set(faces)
for face in faces:
    geom.update(face.edges)
    geom.update(face.verts)
cut = bmesh.ops.bisect_plane(bm, geom=list(geom), dist=0.0001,
                             plane_co=(0, -119, 0), plane_no=(0, 1, 0),
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
    if c.y < -42 and c.z < 119:
        poly.select = True
        selected.append(poly.index)
before = set(bpy.data.objects)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.separate(type="SELECTED")
bpy.ops.object.mode_set(mode="OBJECT")
new_objects = [o for o in set(bpy.data.objects) - before if o.type == "MESH"]
if len(new_objects) != 1:
    raise RuntimeError(f"Unexpected jaw objects: {len(new_objects)}")
jaw = new_objects[0]
if not 100 <= len(jaw.data.polygons) <= 700:
    raise RuntimeError(f"Unexpected jaw faces: {len(jaw.data.polygons)}")
obj.name = "LOD0_upper_plane_test"
jaw.name = "LOD0_lower_jaw_plane_test"
arm = bpy.data.objects["mu_root"]
for track in arm.animation_data.nla_tracks:
    track.mute = True
arm.animation_data.action = bpy.data.actions["action03"]
bpy.context.scene.frame_set(0)
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
report = {"attempt": "v0002-attempt03", "bisect_faces": len(faces),
          "bisect_geom_result": len(cut.get("geom", [])), "selected_faces": len(selected),
          "upper_faces": len(obj.data.polygons), "jaw_faces": len(jaw.data.polygons),
          "status": "needs render review"}
(OUT.parent / "v0002-attempt03-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("ATTEMPT_JSON=" + json.dumps(report))

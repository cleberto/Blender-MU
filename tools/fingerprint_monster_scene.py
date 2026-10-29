"""Produce stable per-LOD geometry/UV/rig/action signatures for comparison."""
import hashlib
import json
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
out = Path(sys.argv[sys.argv.index("--") + 1])


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest().upper()


lods = {}
for name in ("LOD0", "LOD1", "LOD2"):
    obj = bpy.data.objects[name]
    mesh = obj.data
    weights = []
    for vertex in mesh.vertices:
        weights.append(sorted((obj.vertex_groups[g.group].name, round(g.weight, 8))
                              for g in vertex.groups))
    geometry = {
        "vertices": [list(map(lambda n: round(n, 8), vertex.co)) for vertex in mesh.vertices],
        "polygons": [list(poly.vertices) for poly in mesh.polygons],
    }
    materials = [mat.name for mat in mesh.materials]
    uv = [[(round(loop.uv.x, 8), round(loop.uv.y, 8)) for loop in layer.data]
          for layer in mesh.uv_layers]
    lods[name] = {"geometry_sha256": sha(geometry), "material_sha256": sha(materials),
                  "materials": materials, "uv_sha256": sha(uv),
                  "weights_sha256": sha(weights), "weights": weights,
                  "vertices": len(mesh.vertices), "faces": len(mesh.polygons)}

actions = {}
for i in range(7):
    action = bpy.data.actions[f"action{i:02d}"]
    # Blender 5.2 actions can use layered slots; their F-curves are reached via
    # channelbags, with legacy fcurves as fallback.
    curves = []
    if getattr(action, "layers", None):
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag = strip.channelbag(slot, ensure=False)
                    if bag:
                        curves.extend(bag.fcurves)
    else:
        curves = list(action.fcurves)
    record = []
    for curve in curves:
        record.append((curve.data_path, curve.array_index,
                       [(round(point.co.x, 6), round(point.co.y, 8))
                        for point in curve.keyframe_points]))
    actions[action.name] = {"curves": len(record), "sha256": sha(sorted(record))}

images = {}
for image in bpy.data.images:
    if image.packed_file:
        images[image.name] = hashlib.sha256(bytes(image.packed_file.data)).hexdigest().upper()

result = {"scene": bpy.data.filepath, "lods": lods, "actions": actions, "packed_images": images}
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(f"MONSTER_FINGERPRINT={out}")

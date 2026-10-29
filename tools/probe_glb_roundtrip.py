"""Export the untouched HD import to GLB and report structural round-trip parity.

This probes Blender's interchange path; the output is not a new dragon version.
"""
import json
import struct
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "roundtrip-probe.glb"
bpy.ops.object.select_all(action="DESELECT")
for name in ("mu_root", "LOD0", "LOD1", "LOD2"):
    bpy.data.objects[name].hide_set(False)
    bpy.data.objects[name].hide_render = False
    bpy.data.objects[name].select_set(True)
bpy.context.view_layer.objects.active = bpy.data.objects["mu_root"]
bpy.ops.export_scene.gltf(filepath=str(OUT), export_format="GLB", use_selection=True,
                          export_animations=True, export_animation_mode="NLA_TRACKS")
raw = OUT.read_bytes()
length = struct.unpack_from("<I", raw, 12)[0]
gltf = json.loads(raw[20:20 + length])
report = {"path": str(OUT), "meshes": [m.get("name") for m in gltf.get("meshes", [])],
          "animations": [a.get("name") for a in gltf.get("animations", [])],
          "skins": [len(s.get("joints", [])) for s in gltf.get("skins", [])],
          "materials": len(gltf.get("materials", [])), "images": len(gltf.get("images", []))}
(OUT.parent / "roundtrip-probe.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("ROUNDTRIP_JSON=" + json.dumps(report))

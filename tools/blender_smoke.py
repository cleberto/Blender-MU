"""Smoke-test the external MU addon against Blender and inspect the HD dragon.

Run with Blender: blender -b --python tools/blender_smoke.py -- BMD GLB [ADDON_DIRECTORY]
No file is saved and no game data is changed.
"""

import json
import sys
from pathlib import Path

import bpy


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    bmd_path, glb_path = map(Path, args[:2])
    addon_path = Path(args[2]) if len(args) > 2 else Path(__file__).resolve().parents[1] / "vendor" / "mu-blender-addon"
    sys.path.insert(0, str(addon_path))
    import io_scene_muonline

    result = {"blender": bpy.app.version_string}
    try:
        io_scene_muonline.register()
        result["addon_registration"] = "ok"
        bpy.context.scene.muonline_import.load_textures = False
        bpy.ops.import_scene.muonline_bmd(filepath=str(bmd_path))
        result["bmd_import"] = {
            "meshes": len([o for o in bpy.data.objects if o.type == "MESH"]),
            "armatures": len([o for o in bpy.data.objects if o.type == "ARMATURE"]),
            "actions": len(bpy.data.actions),
        }
    except Exception as exc:
        result["addon_error"] = repr(exc)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        bpy.ops.import_scene.gltf(filepath=str(glb_path))
        result["glb_import"] = {
            "meshes": {o.name: {
                "vertices": len(o.data.vertices),
                "faces": len(o.data.polygons),
                "bone02_weighted_vertices": sum(
                    1 for vertex in o.data.vertices
                    for group in vertex.groups
                    if o.vertex_groups[group.group].name == "Bone02" and group.weight > 0.05
                ),
            } for o in bpy.data.objects if o.type == "MESH"},
            "actions": sorted(a.name for a in bpy.data.actions),
        }
    except Exception as exc:
        result["glb_error"] = repr(exc)

    print("AUDIT_JSON=" + json.dumps(result, ensure_ascii=False))


main()

"""Create an inspectable, non-destructive Monster03 Blender baseline.

Run after decode_legacy_textures.py:
blender -b --python tools/prepare_dragon_baseline.py
The HD candidate is visible; the original BMD is a separate hidden collection.
No scale is applied to either source, because Unity calibration is pending.
"""

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "assets" / "original" / "monster03"
HD = ROOT / "models" / "budge-dragon-hd.glb"
TEXTURES = ROOT / "work" / "monster03" / "textures"
OUTPUT = ROOT / "work" / "monster03" / "budge-dragon-baseline-v2.blend"


def move_to_collection(objects, collection):
    for obj in objects:
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        collection.objects.link(obj)


def add_reference_material(obj, image_path, alpha=False):
    image = bpy.data.images.load(str(image_path), check_existing=True)
    image.pack()
    material = bpy.data.materials.new("MU_reference_" + obj.name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = image
    bsdf = nodes.get("Principled BSDF")
    material.node_tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    if alpha:
        material.node_tree.links.new(texture.outputs["Alpha"], bsdf.inputs["Alpha"])
        if hasattr(material, "surface_render_method"):
            material.surface_render_method = "DITHERED"
    obj.data.materials.clear()
    obj.data.materials.append(material)


def main():
    if not (TEXTURES / "p_d.jpg").is_file() or not (TEXTURES / "p_d.png").is_file():
        raise RuntimeError("Run tools/decode_legacy_textures.py first")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sys.path.insert(0, str(ROOT / "vendor" / "mu-blender-addon"))
    from io_scene_muonline.formats.bmd import parse_bmd
    from io_scene_muonline.importer.bmd_importer import import_bmd
    import io_scene_muonline

    io_scene_muonline.register()
    scene = bpy.context.scene
    original_collection = bpy.data.collections.new("00_ORIGINAL_BMD_reference")
    scene.collection.children.link(original_collection)
    bmd = parse_bmd((ORIGINAL / "Monster03.bmd").read_bytes())
    before = set(bpy.data.objects)
    arm, meshes, _actions = import_bmd(bmd, name="Monster03_original", scale=1.0,
                                       load_textures=False, auto_fit=False)
    for action in bpy.data.actions:
        if action.get("muonline_action_index") is not None:
            action.use_fake_user = True  # preserve all seven BMD actions in the saved .blend
    original_objects = set(bpy.data.objects) - before
    move_to_collection(original_objects, original_collection)
    for index, obj in enumerate(meshes):
        add_reference_material(obj, TEXTURES / ("p_d.jpg" if index == 0 else "p_d.png"), index == 1)
    arm["baseline_role"] = "original_unscaled_bmd"
    original_collection.hide_render = True

    hd_collection = bpy.data.collections.new("01_HD_GLB_candidate_v0001")
    scene.collection.children.link(hd_collection)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(HD))
    hd_objects = set(bpy.data.objects) - before
    move_to_collection(hd_objects, hd_collection)
    for obj in hd_objects:
        if obj.type == "ARMATURE":
            obj.show_in_front = False
        if obj.type == "MESH" and obj.name != "LOD0":
            obj.hide_set(True)
            obj.hide_render = True
    hd_collection["baseline_role"] = "received_unmodified_glb"

    # A separate collection prevents accidental confusion between source and candidate.
    # Hide original in viewport after import, while keeping it one click away in Outliner.
    original_collection.hide_viewport = True
    scene.frame_set(0)
    scene.render.film_transparent = False
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.shading.type = "MATERIAL"
                area.spaces.active.region_3d.view_distance = 6.0
                area.spaces.active.region_3d.view_rotation = (0.88, 0.35, 0.31, 0.11)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT))
    report = {
        "blend": str(OUTPUT),
        "blend_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest().upper(),
        "original": {"meshes": len(meshes), "bones": len(arm.data.bones),
                     "actions": len(bmd.actions), "auto_fit": False, "scale": 1.0},
        "hd": {"lod_meshes": {o.name: len(o.data.polygons) for o in hd_objects if o.type == "MESH" and o.name.startswith("LOD")},
               "import_helpers": [o.name for o in hd_objects if o.type == "MESH" and not o.name.startswith("LOD")],
               "armatures": [o.name for o in hd_objects if o.type == "ARMATURE"]},
        "unity_scale_and_axes": "unverified",
        "note": "Reference scene only. Do not export to Unity or approve geometry from this file.",
    }
    (OUTPUT.parent / "baseline-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("BASELINE_JSON=" + json.dumps(report))


if __name__ == "__main__":
    main()

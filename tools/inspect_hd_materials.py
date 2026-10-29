"""Emit a compact, reproducible inventory of the inherited HD materials.

Run with Blender after opening a candidate or baseline scene.  The report is
deliberately data-only: it is used to decide which shader controls are safe to
calibrate without guessing from a viewport screenshot.
"""
import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]


def socket_record(socket):
    link = socket.links[0] if socket.is_linked else None
    return {
        "name": socket.name,
        "linked": bool(link),
        "source": None if not link else f"{link.from_node.name}.{link.from_socket.name}",
        "value": None if socket.is_linked or not hasattr(socket, "default_value") else repr(socket.default_value),
    }


materials = []
for material in sorted(bpy.data.materials, key=lambda item: item.name):
    node_data = []
    for node in material.node_tree.nodes if material.use_nodes and material.node_tree else []:
        inputs = [socket_record(socket) for socket in node.inputs]
        image = getattr(node, "image", None)
        node_data.append({
            "name": node.name,
            "type": node.type,
            "image": None if image is None else image.name,
            "inputs": inputs,
        })
    materials.append({
        "name": material.name,
        "use_nodes": material.use_nodes,
        "blend_method": getattr(material, "surface_render_method", None),
        "nodes": node_data,
    })

objects = {}
for object_name in ("LOD0", "LOD1", "LOD2"):
    obj = bpy.data.objects.get(object_name)
    if obj:
        objects[object_name] = [slot.material.name if slot.material else None for slot in obj.material_slots]

images = []
for image in sorted(bpy.data.images, key=lambda item: item.name):
    images.append({
        "name": image.name,
        "size": list(image.size),
        "packed": image.packed_file is not None,
        "colorspace": image.colorspace_settings.name,
    })

result = {"objects": objects, "materials": materials, "images": images}
out = ROOT / "work" / "monster03" / "hd-material-inventory.json"
out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"materials": len(materials), "images": len(images), "out": str(out)}))

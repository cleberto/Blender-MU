"""Create a non-destructive PBR response study for the inherited HD dragon.

This is intentionally a shader-only candidate.  Mesh positions, UVs, vertex
groups, actions, textures and bones remain inherited; only copied materials on
the three LOD objects are changed.  The constants live here and in the emitted
JSON so the same calibration can be reproduced or tuned for another asset.
"""
import json
import os
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("MU_ASSET_OUTPUT", ROOT / "work" / "monster03" / "v0002-body-material-calibration.blend"))
REPORT = OUT.with_suffix(".material-parameters.json")
PROFILE_PATH = Path(os.environ.get("MU_SURFACE_PROFILE", ROOT / "profiles" / "monster03.surface.json"))
PROFILE = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
if PROFILE.get("profile_type") != "surface_calibration":
    raise RuntimeError(f"Not a surface-calibration profile: {PROFILE_PATH}")
# Deliberately conservative. The received HD material was fully rough (1.0),
# which flattened the normal map under neutral lighting. Values live in the
# profile, so each asset can be rerun and tuned without editing this builder.
CALIBRATION = PROFILE["lods"]


def set_input(node, name, value):
    socket = node.inputs.get(name)
    if socket is not None and not socket.is_linked:
        socket.default_value = value
        return True
    return False


changed = []
for object_name, values in CALIBRATION.items():
    obj = bpy.data.objects[object_name]
    if len(obj.material_slots) != 1 or obj.material_slots[0].material is None:
        raise RuntimeError(f"{object_name} must have exactly one inherited material")
    source = obj.material_slots[0].material
    material = source.copy()
    material.name = f"M03_body_calibrated_{object_name.lower()}"
    obj.material_slots[0].material = material
    nodes = material.node_tree.nodes
    principled = next((node for node in nodes if node.type == "BSDF_PRINCIPLED"), None)
    normal_map = next((node for node in nodes if node.type == "NORMAL_MAP"), None)
    if principled is None or normal_map is None:
        raise RuntimeError(f"{source.name} lacks the expected Principled + Normal Map nodes")
    # Preserve all texture links (including base color and normal map).  Inputs
    # are scalar-only controls, safe to compare against the inherited shader.
    set_input(principled, "Roughness", values["roughness"])
    set_input(principled, "Specular IOR Level", values["specular_ior_level"])
    set_input(normal_map, "Strength", values["normal_strength"])
    changed.append({"object": object_name, "source_material": source.name, "new_material": material.name, **values})

for object_name in CALIBRATION:
    obj = bpy.data.objects[object_name]
    obj["mu_material_calibration"] = "M03_BODY_PBR_01"

report = {
    "study_id": PROFILE["study_id"],
    "profile": str(PROFILE_PATH),
    "scope": PROFILE.get("scope"),
    "intent": "Restore controlled PBR response while preserving the received HD texture and normal map.",
    "changes": changed,
    "preserved": PROFILE["preserve"],
    "not_covered": PROFILE["not_covered"],
    "acceptance": "Compare in turntable and target renderer before promotion; do not infer approval from this build alone.",
}
OUT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
print(json.dumps({"output": str(OUT), "report": str(REPORT), "changed": changed}))

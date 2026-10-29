"""Preserve inherited HD appearance and mark, without cutting, the mouth work zone."""
import hashlib
import json
import math
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "v0002-calibrated-visual-base.blend"
obj = bpy.data.objects["LOD0"]


def geometry_hash():
    data = [
        [tuple(round(x, 7) for x in v.co) for v in obj.data.vertices],
        [tuple(p.vertices) for p in obj.data.polygons],
        [mat.name if mat else None for mat in obj.data.materials],
    ]
    return hashlib.sha256(json.dumps(data, separators=(",", ":")).encode()).hexdigest().upper()


before = geometry_hash()
group = obj.vertex_groups.get("V0002_MOUTH_RETOPO_GUIDE")
if group is None:
    group = obj.vertex_groups.new(name="V0002_MOUTH_RETOPO_GUIDE")
selected = []
strong = []
for vertex in obj.data.vertices:
    p = obj.matrix_world @ vertex.co
    if p.y >= -35 or abs(p.x) >= 22 or p.z <= 102 or p.z >= 141:
        continue
    spatial = math.exp(-0.5 * ((p.y + 61) / 18)**2) * math.exp(-0.5 * ((p.z - 119) / 12)**2)
    bone = 0.0
    for link in vertex.groups:
        if obj.vertex_groups[link.group].name == "Bone02":
            bone = link.weight
    weight = min(1.0, 0.5*spatial + 0.5*bone)
    if weight > 0.08:
        group.add([vertex.index], weight, "REPLACE")
        selected.append(vertex.index)
        if weight >= 0.5:
            strong.append(vertex.index)
after = geometry_hash()
assert before == after, "Calibration must not change inherited mesh geometry or materials"
obj["v0002_role"] = "protected_visual_base_with_mouth_guide"
obj["mouth_guide_policy"] = "guide_only_not_an_approved_cut_or_weight_transfer"
obj["geometry_hash_unchanged"] = before
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
report = {"status": "calibrated_visual_base_only", "source_scene": "work/monster03/budge-dragon-baseline-v2.blend",
          "output_scene": "work/monster03/v0002-calibrated-visual-base.blend",
          "lod0_geometry_material_hash_before": before, "lod0_geometry_material_hash_after": after,
          "mouth_guide": {"name": group.name, "vertices": len(selected), "strong_vertices": len(strong),
                          "world_bounds": {"y_less_than": -35, "abs_x_less_than": 22, "z_between": [102, 141]},
                          "spatial_center": [0, -61, 119], "spatial_sigma_yz": [18, 12],
                          "weight_formula": "min(1, 0.5*spatial_gaussian + 0.5*Bone02_weight)",
                          "status": "guide_only_not_topology_selection"},
          "next_step": "Manual or controlled local retopology guided by the inherited lip/cheek contour and 360 reference"}
(OUT.parent / "calibrated-visual-base-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print("CALIBRATED_BASE_JSON=" + json.dumps(report))

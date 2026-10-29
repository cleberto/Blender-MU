"""Measure Bone01/02/03 weights, bounds and animation structures in baseline .blend."""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "jaw-diagnosis.json"


def bounds(points):
    if not points:
        return None
    return {"min": [round(min(v[i] for v in points), 5) for i in range(3)],
            "max": [round(max(v[i] for v in points), 5) for i in range(3)],
            "mean": [round(sum(v[i] for v in points) / len(points), 5) for i in range(3)]}


def mesh_info(obj):
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    groups = {}
    for name in ("Bip01 Head", "Bone01", "Bone02", "Bone03"):
        group = obj.vertex_groups.get(name)
        if not group:
            continue
        weighted = [(obj.matrix_world @ v.co, next((g.weight for g in v.groups if g.group == group.index), 0.0))
                    for v in obj.data.vertices]
        selected = [p for p, w in weighted if w >= 0.5]
        groups[name] = {"vertices_weight_ge_0_5": len(selected), "bounds": bounds(selected),
                        "weight_sum": round(sum(w for _, w in weighted), 4)}
    return {"vertices": len(obj.data.vertices), "faces": len(obj.data.polygons),
            "bounds": bounds(points), "groups": groups}


def main():
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    result = {"blender": bpy.app.version_string,
              "armatures": [{"name": a.name, "bones": len(a.data.bones),
                             "action": a.animation_data.action.name if a.animation_data and a.animation_data.action else None,
                             "nla_tracks": [{"name": t.name, "strips": [(s.name, s.action.name if s.action else None,
                                                                               s.frame_start, s.frame_end) for s in t.strips]}
                                            for t in a.animation_data.nla_tracks] if a.animation_data else []}
                            for a in arms],
              "actions": [{"name": a.name, "frame_range": list(a.frame_range),
                           "mu_index": a.get("muonline_action_index")} for a in bpy.data.actions],
              "meshes": {o.name: mesh_info(o) for o in bpy.data.objects if o.type == "MESH" and
                         (o.name.startswith("LOD") or o.name.startswith("Monster03_original_mesh"))}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("DIAGNOSIS_JSON=" + json.dumps(result))


if __name__ == "__main__":
    main()

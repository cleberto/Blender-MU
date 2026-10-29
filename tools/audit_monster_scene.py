"""Generic Blender-side technical audit driven by a per-monster JSON profile.

Checks all frames of all declared actions. Technical passes never imply
anatomical, aesthetic or in-game approval; those remain explicit human gates.
"""
import json
import math
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
args = sys.argv[sys.argv.index("--") + 1:]
PROFILE = ROOT / args[0]
OUT = Path(args[1])
profile = json.loads(PROFILE.read_text(encoding="utf-8"))
scene = bpy.context.scene
arm = bpy.data.objects.get(profile["armature"])
checks = []
observations = []


def check(name, passed, detail):
    checks.append({"name": name, "result": "pass" if passed else "fail", "detail": detail})


if arm is None:
    raise RuntimeError(f"Missing armature {profile['armature']}")
for track in arm.animation_data.nla_tracks:
    track.mute = True

lods = []
for name in profile["lod_meshes"]:
    obj = bpy.data.objects.get(name)
    check(f"mesh:{name}", obj is not None and obj.type == "MESH", name)
    if obj is None:
        continue
    triangles = sum(len(poly.vertices) - 2 for poly in obj.data.polygons)
    max_weights = max((len(vertex.groups) for vertex in obj.data.vertices), default=0)
    has_uv = bool(obj.data.uv_layers)
    has_material = bool(obj.data.materials)
    lods.append({"name": name, "vertices": len(obj.data.vertices), "triangles": triangles,
                 "materials": len(obj.data.materials), "uv_layers": len(obj.data.uv_layers),
                 "max_weights_per_vertex": max_weights})
    check(f"uv:{name}", has_uv, f"{len(obj.data.uv_layers)} UV layers")
    check(f"materials:{name}", has_material, f"{len(obj.data.materials)} materials")
    check(f"weights:{name}", max_weights <= 4, f"max {max_weights}")

mesh = bpy.data.objects.get(profile["lod_meshes"][0])
groups = {}
if mesh:
    for region, bones in profile["regions"].items():
        group_ids = {mesh.vertex_groups[bone].index for bone in bones if bone in mesh.vertex_groups}
        indices = [vertex.index for vertex in mesh.data.vertices
                   if any(g.group in group_ids and g.weight >= 0.25 for g in vertex.groups)]
        groups[region] = indices
        check(f"region:{region}", bool(indices), f"{len(indices)} LOD0 vertices")

action_reports = {}
for action_name in profile["actions"]:
    action = bpy.data.actions.get(action_name)
    check(f"action:{action_name}", action is not None, action_name)
    if action is None or mesh is None:
        continue
    arm.animation_data.action = action
    start = math.floor(action.frame_range[0])
    end = math.ceil(action.frame_range[1])
    samples = []
    finite = True
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        vertices = evaluated.data.vertices
        coords = [evaluated.matrix_world @ v.co for v in vertices]
        if not all(math.isfinite(value) for p in coords for value in p):
            finite = False
        regions = {}
        for region, indices in groups.items():
            if not indices:
                continue
            points = [coords[i] for i in indices]
            regions[region] = {
                "bounds_min": [round(min(p[k] for p in points), 3) for k in range(3)],
                "bounds_max": [round(max(p[k] for p in points), 3) for k in range(3)]
            }
        samples.append({"frame": frame, "regions": regions})
    check(f"finite_deformation:{action_name}", finite, f"frames {start}..{end}")
    action_reports[action_name] = {"start": start, "end": end, "samples": samples}

mouth_objects = [obj.name for obj in bpy.data.objects if obj.name.startswith("MouthInterior_")]
if profile.get("requires_mouth_interior"):
    check("mouth_interior", bool(mouth_objects), mouth_objects or "No modeled mouth interior")

technical_failures = [item["name"] for item in checks if item["result"] == "fail"]
pending_human = profile.get("human_gates", [])
result = {
    "schema_version": 1,
    "asset_id": profile["asset_id"],
    "profile": str(PROFILE.relative_to(ROOT)).replace("\\", "/"),
    "scene": bpy.data.filepath,
    "blender_version": bpy.app.version_string,
    "technical_status": "fail" if technical_failures else "pass",
    "release_status": "blocked" if technical_failures or pending_human else "eligible_for_review",
    "technical_failures": technical_failures,
    "pending_human_gates": pending_human,
    "lods": lods,
    "checks": checks,
    "actions": action_reports,
    "observations": observations,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print("MONSTER_AUDIT_JSON=" + json.dumps({"technical_status": result["technical_status"],
                                       "release_status": result["release_status"],
                                       "technical_failures": technical_failures,
                                       "actions_checked": list(action_reports)}))

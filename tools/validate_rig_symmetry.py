"""Blender-first technical gates for localized symmetry and mouth deformation.

The validator is deliberately non-destructive. It does not symmetrize meshes,
change weights, clamp animation or declare artistic/game approval.

Run after `--` with a profile, for example:
    blender candidate.blend -b --python-exit-code 1 \
      --python tools/validate_rig_symmetry.py -- \
      --profile profiles/monster03.json \
      --report work/monster03/rig-validation.json \
      --upper-mesh MOUTH_UPPER --lower-mesh MOUTH_LOWER

Expected optional mouth roles:
  * MOUTH_UPPER: upper jaw/maxilla shell; no Bone02 influence.
  * MOUTH_LOWER: lower jaw shell; driven by Bone02.
  * Vertex groups MOUTH_UPPER_RIM and MOUTH_LOWER_RIM enable opening measurement.

Every declared action is evaluated at every integer frame. Collision uses BVH
between upper and lower mouth objects, never a mesh against itself.

Exit codes: 0 = technical gates pass, 1 = failed gate, 2 = missing evidence.
Even exit 0 requires the profile's human visual and target-runtime gates.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector, kdtree
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--mesh", help="Defaults to the profile's first LOD")
    parser.add_argument("--armature", help="Defaults to the profile armature")
    parser.add_argument("--symmetry-region", default="head")
    parser.add_argument("--symmetry-axis", choices=["X", "Y", "Z"], default="X")
    parser.add_argument("--absolute-tolerance", type=float, default=0.005,
                        help="Blender mesh-local units, not assumed meters")
    parser.add_argument("--relative-tolerance", type=float, default=0.001,
                        help="Fraction of the selected region's bounding-box diagonal")
    parser.add_argument("--region-weight", type=float, default=0.5)
    parser.add_argument("--exempt-group", default="SYMMETRY_EXEMPT")
    parser.add_argument("--jaw-bone")
    parser.add_argument("--upper-mesh")
    parser.add_argument("--lower-mesh")
    parser.add_argument("--upper-rim-group", default="MOUTH_UPPER_RIM")
    parser.add_argument("--lower-rim-group", default="MOUTH_LOWER_RIM")
    parser.add_argument("--min-opening-ratio", type=float, default=0.02,
                        help="Minimum rim-distance range / head bounds diagonal")
    parser.add_argument("--max-colliding-pairs", type=int, default=0)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(argv)


def weight_for(vertex, group_index):
    return next((group.weight for group in vertex.groups if group.group == group_index), 0.0)


def bone_vertices(mesh, bone_names, threshold):
    group_ids = {mesh.vertex_groups[name].index for name in bone_names if name in mesh.vertex_groups}
    return [vertex.index for vertex in mesh.data.vertices
            if any(weight_for(vertex, group_id) >= threshold for group_id in group_ids)]


def group_vertices(mesh, name):
    group = mesh.vertex_groups.get(name)
    if group is None:
        return []
    return [vertex.index for vertex in mesh.data.vertices if weight_for(vertex, group.index) > 0.5]


def mesh_bounds(points):
    minimum = [min(point[i] for point in points) for i in range(3)]
    maximum = [max(point[i] for point in points) for i in range(3)]
    diagonal = math.sqrt(sum((maximum[i] - minimum[i]) ** 2 for i in range(3)))
    return minimum, maximum, diagonal


def check_symmetry(mesh, bone_names, args):
    if not bone_names:
        return {"status": "blocked", "reason": "No symmetry-region bones configured"}
    indices = bone_vertices(mesh, bone_names, args.region_weight)
    if len(indices) < 2:
        return {"status": "blocked", "reason": "Fewer than two vertices in symmetry region",
                "bones": bone_names}
    exempt = set(group_vertices(mesh, args.exempt_group))
    indices = [index for index in indices if index not in exempt]
    points = {index: mesh.data.vertices[index].co.copy() for index in indices}
    minimum, maximum, diagonal = mesh_bounds(list(points.values()))
    tolerance = max(args.absolute_tolerance, args.relative_tolerance * diagonal)
    axis = "XYZ".index(args.symmetry_axis)
    tree = kdtree.KDTree(len(indices))
    for index in indices:
        tree.insert(points[index], index)
    tree.balance()
    failures = []
    distances = []
    centerline = 0
    for index in indices:
        point = points[index]
        if abs(point[axis]) <= tolerance:
            centerline += 1
            continue
        mirrored = point.copy()
        mirrored[axis] = -mirrored[axis]
        _co, other_index, distance = tree.find(mirrored)
        distances.append(distance)
        if distance > tolerance:
            failures.append({"vertex": index, "mirror_vertex": other_index,
                             "distance": distance, "position": list(point)})
    failures.sort(key=lambda item: item["distance"], reverse=True)
    return {
        "status": "fail" if failures else "pass",
        "bones": bone_names, "axis": args.symmetry_axis,
        "units": "mesh-local Blender units; physical scale not inferred",
        "region_vertices": len(indices), "centerline_vertices_skipped": centerline,
        "evaluated_vertices": len(distances), "unmatched_vertices": len(failures),
        "unmatched_ratio": len(failures) / len(distances) if distances else None,
        "bounds_min": minimum, "bounds_max": maximum, "bounds_diagonal": diagonal,
        "tolerance": {"absolute": args.absolute_tolerance,
                      "relative_to_region_diagonal": args.relative_tolerance,
                      "effective": tolerance},
        "distance_max": max(distances, default=None),
        "worst": failures[:20],
        "exempt_group": args.exempt_group,
        "note": "Diagnostic only; intentional asymmetry needs an explicit exemption and visual review.",
    }


def evaluated_geometry(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    points = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    polygons = [tuple(poly.vertices) for poly in mesh.polygons]
    evaluated.to_mesh_clear()
    return points, polygons


def set_action(armature, action):
    animation = armature.animation_data
    animation.action = action
    # Blender 4.4+ slotted actions: select a compatible slot when one exists.
    if hasattr(animation, "action_slot") and hasattr(action, "slots") and len(action.slots):
        animation.action_slot = action.slots[0]


def centroid(points, indices):
    if not indices or max(indices) >= len(points):
        return None
    selected = [points[index] for index in indices]
    return sum(selected, Vector((0.0, 0.0, 0.0))) / len(selected)


def main():
    args = parse_args()
    profile_path = args.profile if args.profile.is_absolute() else ROOT / args.profile
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    mesh_name = args.mesh or profile["lod_meshes"][0]
    armature_name = args.armature or profile["armature"]
    mesh = bpy.data.objects.get(mesh_name)
    armature = bpy.data.objects.get(armature_name)
    if mesh is None or mesh.type != "MESH":
        raise RuntimeError(f"Missing mesh: {mesh_name}")
    if armature is None or armature.type != "ARMATURE":
        raise RuntimeError(f"Missing armature: {armature_name}")
    if not any(modifier.type == "ARMATURE" and modifier.object == armature
               for modifier in mesh.modifiers):
        raise RuntimeError(f"Mesh {mesh_name} is not deformed by armature {armature_name}")

    regions = profile.get("regions", {})
    head_bones = regions.get(args.symmetry_region, [])
    jaw_bone = args.jaw_bone or (regions.get("jaw") or [None])[0]
    checks = {"symmetry": check_symmetry(mesh, head_bones, args)}

    if not jaw_bone:
        jaw_indices = []
        checks["jaw_weights"] = {"status": "blocked", "reason": "No jaw bone configured"}
    else:
        jaw_indices = bone_vertices(mesh, [jaw_bone], 0.01)
        checks["jaw_weights"] = {
            "status": "pass" if jaw_indices else "fail", "bone": jaw_bone,
            "influenced_vertices": len(jaw_indices),
            "note": "Bone influence alone does not prove that a mouth opens correctly.",
        }

    upper = bpy.data.objects.get(args.upper_mesh) if args.upper_mesh else None
    lower = bpy.data.objects.get(args.lower_mesh) if args.lower_mesh else None
    mouth_required = bool(profile.get("requires_mouth_interior")) or bool(args.upper_mesh or args.lower_mesh)
    upper_rim = group_vertices(upper, args.upper_rim_group) if upper else []
    lower_rim = group_vertices(lower, args.lower_rim_group) if lower else []
    parts_ready = bool(upper and lower and upper.type == "MESH" and lower.type == "MESH")
    rims_ready = bool(upper_rim and lower_rim)

    if mouth_required and not parts_ready:
        checks["mouth_parts"] = {"status": "blocked",
                                 "reason": "Supply separate upper/lower mouth meshes for collision validation"}
    elif mouth_required:
        leaked = bone_vertices(upper, [jaw_bone], 0.01) if jaw_bone else []
        checks["mouth_parts"] = {"status": "fail" if leaked else "pass",
                                 "upper": upper.name, "lower": lower.name,
                                 "upper_vertices_with_jaw_weight": len(leaked)}
    if mouth_required and not rims_ready:
        checks["mouth_opening"] = {"status": "blocked",
                                   "reason": "Create upper/lower rim vertex groups to measure opening"}

    animation = armature.animation_data
    if animation is None:
        raise RuntimeError(f"Armature has no animation_data: {armature_name}")
    original_action = animation.action
    original_slot = getattr(animation, "action_slot", None)
    original_frame = bpy.context.scene.frame_current
    track_mutes = [(track, track.mute) for track in animation.nla_tracks]
    action_reports = {}
    try:
        for track, _mute in track_mutes:
            track.mute = True
        for action_name in profile["actions"]:
            action = bpy.data.actions.get(action_name)
            if action is None:
                action_reports[action_name] = {"status": "fail", "reason": "Action missing"}
                continue
            set_action(armature, action)
            start = math.floor(action.frame_range[0])
            end = math.ceil(action.frame_range[1])
            report = {"status": "pass", "start": start, "end": end,
                      "frames_evaluated": 0, "nonfinite_frames": [],
                      "collision_frames": [], "rim_distance_min": None,
                      "rim_distance_max": None}
            rim_distances = []
            for frame in range(start, end + 1):
                bpy.context.scene.frame_set(frame)
                depsgraph = bpy.context.evaluated_depsgraph_get()
                points, _polygons = evaluated_geometry(mesh, depsgraph)
                report["frames_evaluated"] += 1
                if not all(math.isfinite(value) for point in points for value in point):
                    report["nonfinite_frames"].append(frame)
                if parts_ready:
                    upper_points, upper_polygons = evaluated_geometry(upper, depsgraph)
                    lower_points, lower_polygons = evaluated_geometry(lower, depsgraph)
                    upper_bvh = BVHTree.FromPolygons(upper_points, upper_polygons, epsilon=0.0)
                    lower_bvh = BVHTree.FromPolygons(lower_points, lower_polygons, epsilon=0.0)
                    overlaps = upper_bvh.overlap(lower_bvh)
                    if len(overlaps) > args.max_colliding_pairs:
                        report["collision_frames"].append({"frame": frame, "pairs": len(overlaps)})
                    if rims_ready:
                        upper_center = centroid(upper_points, upper_rim)
                        lower_center = centroid(lower_points, lower_rim)
                        if upper_center is not None and lower_center is not None:
                            rim_distances.append((lower_center - upper_center).length)
            if report["nonfinite_frames"] or report["collision_frames"]:
                report["status"] = "fail"
            if rim_distances:
                report["rim_distance_min"] = min(rim_distances)
                report["rim_distance_max"] = max(rim_distances)
                report["rim_distance_range"] = max(rim_distances) - min(rim_distances)
            action_reports[action_name] = report
    finally:
        for track, mute in track_mutes:
            track.mute = mute
        animation.action = original_action
        if original_slot is not None and hasattr(animation, "action_slot"):
            animation.action_slot = original_slot
        bpy.context.scene.frame_set(original_frame)

    checks["actions"] = {
        "status": "fail" if any(report["status"] == "fail" for report in action_reports.values()) else "pass",
        "declared_actions": len(profile["actions"]),
        "evaluated_actions": len(action_reports),
        "every_integer_frame": True,
    }
    if parts_ready:
        collision_frames = sum((report["collision_frames"] for report in action_reports.values()), [])
        checks["mouth_collision"] = {"status": "fail" if collision_frames else "pass",
                                     "frames": collision_frames[:100],
                                     "total_failed_frames": len(collision_frames)}
    if rims_ready:
        diagonal = checks["symmetry"].get("bounds_diagonal", 0.0)
        ranges = [report["rim_distance_range"] for report in action_reports.values()
                  if "rim_distance_range" in report]
        maximum_range = max(ranges, default=0.0)
        required = diagonal * args.min_opening_ratio
        checks["mouth_opening"] = {"status": "pass" if maximum_range >= required else "fail",
                                   "maximum_rim_distance_range": maximum_range,
                                   "required_range": required,
                                   "ratio_to_head_diagonal": args.min_opening_ratio,
                                   "note": "A range pass does not rule out tearing; inspect motion renders."}

    failed = [name for name, check in checks.items() if check["status"] == "fail"]
    blocked = [name for name, check in checks.items() if check["status"] == "blocked"]
    result = {
        "schema_version": 1,
        "scene": bpy.data.filepath,
        "blender_version": bpy.app.version_string,
        "asset_id": profile["asset_id"],
        "profile": profile_path.relative_to(ROOT).as_posix() if profile_path.is_relative_to(ROOT) else str(profile_path),
        "mesh": mesh.name, "armature": armature.name,
        "technical_status": "fail" if failed else ("blocked" if blocked else "pass"),
        "release_status": "requires_human_review",
        "failed_gates": failed, "blocked_gates": blocked,
        "pending_human_gates": profile.get("human_gates", []),
        "checks": checks, "actions": action_reports,
        "limitations": [
            "No automatic symmetrization or weight repair is performed.",
            "Mouth collision is checked only between the supplied upper/lower objects.",
            "Technical checks do not prove anatomy, UVs, shading, identity or target-runtime quality.",
        ],
    }
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("RIG_VALIDATION_JSON=" + json.dumps({
        "technical_status": result["technical_status"], "failed_gates": failed,
        "blocked_gates": blocked, "report": str(report_path),
        "actions": {name: {"frames": report.get("frames_evaluated", 0), "status": report["status"]}
                    for name, report in action_reports.items()},
    }, ensure_ascii=False))
    return 1 if failed else (2 if blocked else 0)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"RIG_VALIDATION_ERROR: {error}", file=sys.stderr)
        raise

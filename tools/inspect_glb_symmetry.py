"""Measure bilateral mesh symmetry directly in a glTF 2.0 binary file.

This is a diagnostic, not an automatic repair. It never changes the GLB.
No third-party packages are required.

Example:
    py -3.9 tools/inspect_glb_symmetry.py models/budge-dragon-hd.glb \
        --mesh LOD0 --bone "Bip01 Head" --output work/monster03/glb-symmetry.json

Exit codes: 0 = within tolerance, 2 = asymmetry found, 1 = input/usage error.
"""
import argparse
import hashlib
import json
import math
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

COMPONENT_TYPES = {
    5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2),
    5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4),
}
TYPE_COUNTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def load_glb(path):
    raw = path.read_bytes()
    if len(raw) < 28:
        raise ValueError("File is too small to be a GLB")
    magic, version, declared_length = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(raw):
        raise ValueError("Expected a complete glTF 2.0 binary file")
    json_length, json_type = struct.unpack_from("<II", raw, 12)
    if json_type != 0x4E4F534A:
        raise ValueError("First GLB chunk is not JSON")
    document = json.loads(raw[20:20 + json_length])
    binary_header = 20 + json_length
    binary_length, binary_type = struct.unpack_from("<II", raw, binary_header)
    if binary_type != 0x004E4942:
        raise ValueError("Second GLB chunk is not BIN")
    binary = raw[binary_header + 8:binary_header + 8 + binary_length]
    return raw, document, binary


def read_accessor(document, binary, index):
    accessor = document["accessors"][index]
    if "sparse" in accessor:
        raise ValueError("Sparse accessors are not supported by this diagnostic")
    view = document["bufferViews"][accessor["bufferView"]]
    code, component_size = COMPONENT_TYPES[accessor["componentType"]]
    components = TYPE_COUNTS[accessor["type"]]
    count = accessor["count"]
    stride = view.get("byteStride", component_size * components)
    offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    rows = []
    unpack = struct.Struct("<" + code * components).unpack_from
    for row in range(count):
        rows.append(unpack(binary, offset + row * stride))
    return rows


def percentile(sorted_values, fraction):
    if not sorted_values:
        return None
    position = (len(sorted_values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    return sorted_values[lower] * (upper - position) + sorted_values[upper] * (position - lower)


def bounds(points):
    return {
        "min": [min(point[axis] for point in points) for axis in range(3)],
        "max": [max(point[axis] for point in points) for axis in range(3)],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("glb", type=Path)
    parser.add_argument("--mesh", default="LOD0")
    parser.add_argument("--bone", default="Bip01 Head",
                        help="Restrict measurement to vertices influenced by this joint; use an empty string for the whole mesh")
    parser.add_argument("--weight", type=float, default=0.5)
    parser.add_argument("--axis", choices=["x", "y", "z"], default="x")
    parser.add_argument("--absolute-tolerance", type=float, default=0.005,
                        help="Tolerance in GLB mesh units, not assumed meters")
    parser.add_argument("--relative-tolerance", type=float, default=0.001,
                        help="Fraction of the measured region's bounding-box diagonal")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    raw, document, binary = load_glb(args.glb)
    mesh_index = next((i for i, mesh in enumerate(document.get("meshes", []))
                       if mesh.get("name") == args.mesh), None)
    if mesh_index is None:
        raise ValueError(f"Mesh not found: {args.mesh}")
    primitives = document["meshes"][mesh_index]["primitives"]
    if len(primitives) != 1:
        raise ValueError("This diagnostic expects exactly one primitive in the selected mesh")
    attributes = primitives[0]["attributes"]
    positions = read_accessor(document, binary, attributes["POSITION"])
    selected = set(range(len(positions)))

    if args.bone:
        joint_node = next((i for i, node in enumerate(document.get("nodes", []))
                           if node.get("name") == args.bone), None)
        if joint_node is None:
            raise ValueError(f"Joint node not found: {args.bone}")
        mesh_node = next((node for node in document.get("nodes", [])
                          if node.get("mesh") == mesh_index and "skin" in node), None)
        if mesh_node is None:
            raise ValueError("Selected mesh is not skinned; use --bone '' for a static-mesh check")
        skin = document["skins"][mesh_node["skin"]]
        try:
            joint_index = skin["joints"].index(joint_node)
        except ValueError as exc:
            raise ValueError(f"Joint {args.bone} is not present in the mesh skin") from exc
        joints = read_accessor(document, binary, attributes["JOINTS_0"])
        weights = read_accessor(document, binary, attributes["WEIGHTS_0"])
        selected = set()
        for vertex, (vertex_joints, vertex_weights) in enumerate(zip(joints, weights)):
            influence = max((weight for joint, weight in zip(vertex_joints, vertex_weights)
                             if joint == joint_index), default=0.0)
            if influence >= args.weight:
                selected.add(vertex)

    if len(selected) < 2:
        raise ValueError("Fewer than two vertices selected")
    axis = "xyz".index(args.axis)
    mirror_axis = axis
    region_points = [positions[index] for index in sorted(selected)]
    region_bounds = bounds(region_points)
    diagonal = math.sqrt(sum((region_bounds["max"][i] - region_bounds["min"][i]) ** 2
                             for i in range(3)))
    tolerance = max(args.absolute_tolerance, args.relative_tolerance * diagonal)

    # A brute-force search is intentional: the head region is small, and this keeps
    # the diagnostic dependency-free and reproducible with the repository's Python.
    distances = {}
    for index in sorted(selected):
        point = positions[index]
        if abs(point[axis]) <= tolerance:
            continue  # center seam is checked separately by the tolerance itself
        target = list(point)
        target[mirror_axis] = -target[mirror_axis]
        best_squared = math.inf
        for other in selected:
            candidate = positions[other]
            squared = sum((target[i] - candidate[i]) ** 2 for i in range(3))
            if squared < best_squared:
                best_squared = squared
        distances[index] = math.sqrt(best_squared)

    ordered = sorted(distances.values())
    failures = {index: distance for index, distance in distances.items() if distance > tolerance}
    worst = sorted(failures.items(), key=lambda item: item[1], reverse=True)[:20]
    result = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": args.glb.as_posix(),
        "source_sha256": hashlib.sha256(raw).hexdigest().upper(),
        "mesh": args.mesh,
        "mesh_vertices": len(positions),
        "region": {"bone": args.bone or None, "minimum_weight": args.weight,
                   "selected_vertices": len(selected), "bounds": region_bounds,
                   "bounds_diagonal": diagonal},
        "axis": args.axis,
        "units": "GLB mesh units; physical unit scale not inferred",
        "tolerance": {"absolute": args.absolute_tolerance,
                      "relative_to_region_diagonal": args.relative_tolerance,
                      "effective": tolerance},
        "symmetry": {
            "status": "fail" if failures else "pass",
            "evaluated_vertices": len(distances),
            "unmatched_vertices": len(failures),
            "unmatched_ratio": len(failures) / len(distances) if distances else None,
            "distance_percentiles": {str(p): percentile(ordered, p / 100)
                                     for p in (0, 50, 90, 95, 99, 100)},
            "worst": [{"vertex": index, "distance": distance,
                       "position": positions[index]} for index, distance in worst],
        },
        "note": "Measurement only. Do not globally symmetrize a rigged/UV-mapped asset from this report.",
    }
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(json.dumps({"mesh": args.mesh, "region_vertices": len(selected),
                      "effective_tolerance": tolerance,
                      "unmatched_vertices": len(failures),
                      "evaluated_vertices": len(distances),
                      "status": result["symmetry"]["status"]}, ensure_ascii=False))
    return 2 if failures else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, IndexError, struct.error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)

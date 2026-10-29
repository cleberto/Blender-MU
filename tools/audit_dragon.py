"""Read-only audit of the original Budge Dragon BMD and an HD GLB.

Usage: py -3.9 tools/audit_dragon.py SOURCE_BMD HD_GLB [ADDON_DIRECTORY]
"""

import json
import math
import struct
import sys
from pathlib import Path


def main():
    bmd_path, glb_path = map(Path, sys.argv[1:3])
    addon_path = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(__file__).resolve().parents[1] / "vendor" / "mu-blender-addon"
    sys.path.insert(0, str(addon_path))
    from io_scene_muonline.formats.bmd import parse_bmd

    bmd = parse_bmd(bmd_path.read_bytes())
    raw = glb_path.read_bytes()
    if raw[:4] != b"glTF" or struct.unpack_from("<I", raw, 4)[0] != 2:
        raise ValueError("Expected glTF 2.0 binary")
    json_length, json_type = struct.unpack_from("<II", raw, 12)
    if json_type != 0x4E4F534A:
        raise ValueError("Missing GLB JSON chunk")
    gltf = json.loads(raw[20 : 20 + json_length])

    def motion(bone):
        result = []
        for action in bone.matrixes:
            if not action.positions:
                result.append(None)
                continue
            p0, r0 = action.positions[0], action.rotations[0]
            result.append({
                "position_span": round(max(math.dist(p0, p) for p in action.positions), 4),
                "rotation_span_radians": round(max(math.dist(r0, r) for r in action.rotations), 4),
            })
        return result

    print(json.dumps({
        "bmd": {
            "version": bmd.version,
            "name": bmd.name,
            "meshes": [{"texture": m.texture_path, "vertices": len(m.vertices),
                        "triangles": len(m.triangles)} for m in bmd.meshes],
            "actions": [{"keys": a.num_animation_keys,
                         "lock_positions": a.lock_positions} for a in bmd.actions],
            "bones": [{"index": i, "name": b.name, "parent": b.parent,
                       "vertices": sum(1 for m in bmd.meshes for node, _ in m.vertices if node == i),
                       **({"motion_by_action": motion(b)} if b.name in
                          ("Bip01 Head", "Bone01", "Bone02", "Bone03") else {})}
                      for i, b in enumerate(bmd.bones)],
        },
        "glb": {
            "asset_extras": gltf.get("asset", {}).get("extras"),
            "animations": [a.get("name") for a in gltf.get("animations", [])],
            "bone02_animation_channels": [
                {"action": a.get("name"), "paths": [
                    c.get("target", {}).get("path") for c in a.get("channels", [])
                    if gltf["nodes"][c.get("target", {}).get("node", -1)].get("name") == "Bone02"
                ]} for a in gltf.get("animations", [])
            ],
            "skins": [{"joints": len(s.get("joints", []))} for s in gltf.get("skins", [])],
            "meshes": [m.get("name") for m in gltf.get("meshes", [])],
            "nodes": [{"index": i, "name": n.get("name"), "mesh": n.get("mesh")}
                      for i, n in enumerate(gltf.get("nodes", []))
                      if "mesh" in n or any(k in (n.get("name") or "").lower()
                                         for k in ("jaw", "head", "bone01", "bone02", "bone03"))],
        },
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

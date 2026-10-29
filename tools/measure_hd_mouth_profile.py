"""Output world-space vertical ranges of upper and lower muzzle on action00."""
import json
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
obj = bpy.data.objects["LOD0"]
arm = bpy.data.objects["mu_root"]
for track in arm.animation_data.nla_tracks:
    track.mute = True
arm.animation_data.action = bpy.data.actions["action00"]
bpy.context.scene.frame_set(0)
mesh = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
jaw_group = obj.vertex_groups["Bone02"].index
rows = []
for y0 in range(-78, -38, 5):
    for side in (-1, 1):
        for region in ("jaw", "upper"):
            points = []
            for v in mesh.vertices:
                p = obj.matrix_world @ v.co
                if y0 <= p.y < y0 + 5 and (p.x * side) > 2 and abs(p.x) < 18 and 105 < p.z < 155:
                    w = sum(g.weight for g in v.groups if g.group == jaw_group)
                    if (region == "jaw" and w > 0.9) or (region == "upper" and w < 0.1):
                        points.append(p)
            if points:
                rows.append({"y": y0, "side": side, "region": region, "count": len(points),
                             "z_min": round(min(p.z for p in points), 2),
                             "z_max": round(max(p.z for p in points), 2),
                             "x_min": round(min(abs(p.x) for p in points), 2),
                             "x_max": round(max(abs(p.x) for p in points), 2)})
path = ROOT / "work" / "monster03" / "hd-mouth-profile.json"
path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
print("MOUTH_PROFILE=" + json.dumps(rows))

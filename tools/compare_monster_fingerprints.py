"""Compare inherited baseline with a candidate and locate changed skinning."""
import json
import sys
from pathlib import Path

original = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
candidate = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
out = Path(sys.argv[3])
lods = {}
for name, before in original["lods"].items():
    after = candidate["lods"][name]
    changed_weights = [index for index, (a, b) in enumerate(zip(before["weights"], after["weights"])) if a != b]
    lods[name] = {
        "geometry_identical": before["geometry_sha256"] == after["geometry_sha256"],
        "materials_identical": before.get("material_sha256") == after.get("material_sha256"),
        "uv_identical": before["uv_sha256"] == after["uv_sha256"],
        "weights_identical": before["weights_sha256"] == after["weights_sha256"],
        "changed_weight_vertex_count": len(changed_weights),
        "changed_weight_vertices": changed_weights,
    }
actions = {name: before["sha256"] == candidate["actions"][name]["sha256"]
           for name, before in original["actions"].items()}
images = original["packed_images"] == candidate["packed_images"]
result = {"lods": lods, "actions_identical": actions, "packed_images_identical": images,
          "body_preservation_pass": all(row["geometry_identical"] and row["uv_identical"] for row in lods.values())
                                    and all(actions.values()) and images
                                    and lods["LOD1"]["weights_identical"]
                                    and lods["LOD2"]["weights_identical"]}
out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"body_preservation_pass": result["body_preservation_pass"],
                  "weight_changes": {name: row["changed_weight_vertex_count"] for name, row in lods.items()}}))

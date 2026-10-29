"""Dependency-free validator for the compact surface-calibration profile."""
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
path = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "profiles/monster03.surface.json")
profile = json.loads(path.read_text(encoding="utf-8"))
required = {"schema_version", "profile_type", "asset_id", "version", "study_id", "lods", "preserve", "human_gates"}
allowed = required | {"scope", "not_covered", "notes"}
missing, extra = required - profile.keys(), profile.keys() - allowed
assert not missing, f"missing: {sorted(missing)}"
assert not extra, f"unknown: {sorted(extra)}"
assert profile["schema_version"] == 1
assert profile["profile_type"] == "surface_calibration"
assert re.fullmatch(r"v\d{4}", profile["version"])
assert re.fullmatch(r"[A-Z0-9_]+", profile["study_id"])
assert isinstance(profile["lods"], dict) and profile["lods"]
for lod, values in profile["lods"].items():
    assert isinstance(lod, str) and set(values) == {"roughness", "specular_ior_level", "normal_strength"}
    assert 0 <= values["roughness"] <= 1
    assert 0 <= values["specular_ior_level"] <= 1
    assert 0 <= values["normal_strength"] <= 4
for key in ("preserve", "human_gates"):
    assert isinstance(profile[key], list) and all(isinstance(value, str) for value in profile[key])
print(f"surface profile valid: {path.relative_to(ROOT)} ({len(profile['lods'])} LODs)")

"""Small, dependency-free registry for MU asset experiments.

Use `py -3.9 tools/registry.py --help` from any directory.
"""

import argparse
import copy
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog"
SCHEMAS = ROOT / "schemas"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def asset_path(asset_id):
    parts = asset_id.split(":")
    if len(parts) != 3 or parts[0] != "mu" or not re.fullmatch(r"[a-z_]+", parts[1]) or not re.fullmatch(r"[a-z0-9_-]+", parts[2]):
        raise ValueError("asset ID must be mu:<kind>:<slug>")
    return CATALOG / "assets" / parts[1] / parts[2] / "asset.json"


def version_path(asset_id, version):
    if not re.fullmatch(r"v[0-9]{4}", version):
        raise ValueError("version must look like v0001")
    return asset_path(asset_id).parent / "versions" / (version + ".json")


def validate_shape(value, schema, where, errors, root_schema=None):
    root_schema = root_schema or schema
    if "$ref" in schema:
        target = root_schema
        for part in schema["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        return validate_shape(value, target, where, errors, root_schema)
    expected = schema.get("type")
    types = expected if isinstance(expected, list) else [expected]
    checks = {"object": lambda x: isinstance(x, dict), "array": lambda x: isinstance(x, list),
              "string": lambda x: isinstance(x, str), "integer": lambda x: isinstance(x, int) and not isinstance(x, bool),
              "null": lambda x: x is None}
    if expected and not any(checks[t](value) for t in types):
        errors.append(f"{where}: expected {expected}")
        return
    if "const" in schema and value != schema["const"]:
        errors.append(f"{where}: expected {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: invalid value {value!r}")
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{where}: invalid format {value!r}")
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{where}: too short")
        if schema.get("format") == "date-time":
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{where}: invalid date-time")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{where}: missing {key}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in value.keys() - props.keys():
                errors.append(f"{where}: unknown {key}")
        for key in value.keys() & props.keys():
            validate_shape(value[key], props[key], f"{where}.{key}", errors, root_schema)
    if isinstance(value, list):
        if schema.get("uniqueItems") and len(set(map(json.dumps, value))) != len(value):
            errors.append(f"{where}: duplicate array item")
        for i, item in enumerate(value):
            if "items" in schema:
                validate_shape(item, schema["items"], f"{where}[{i}]", errors, root_schema)


def checked_file(entry, where, errors):
    raw = entry["path"]
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts or ":" in raw:
        errors.append(f"{where}: path must be project-relative: {raw}")
        return
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        errors.append(f"{where}: missing file {raw}")
        return
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest.lower() != entry["sha256"].lower():
        errors.append(f"{where}: SHA-256 mismatch for {raw}")


def checked_reference(raw, where, errors):
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts or ":" in raw or not (ROOT / relative).is_file():
        errors.append(f"{where}: missing or unsafe reference {raw}")


def validate():
    errors = []
    assets = {}
    versions = {}
    runs = {}
    for path in sorted((CATALOG / "assets").glob("*/*/asset.json")):
        obj = read(path)
        validate_shape(obj, read(SCHEMAS / "asset.schema.json"), str(path.relative_to(ROOT)), errors)
        aid = obj.get("id")
        if aid in assets:
            errors.append(f"duplicate asset ID: {aid}")
        assets[aid] = obj
        if path != asset_path(aid):
            errors.append(f"{aid}: ID/path mismatch")
        for file in obj.get("sources", []):
            checked_file(file, aid, errors)
        for v in obj.get("versions", []):
            vp = version_path(aid, v)
            if not vp.is_file():
                errors.append(f"{aid}: missing version {v}")
                continue
            vo = read(vp)
            validate_shape(vo, read(SCHEMAS / "version.schema.json"), str(vp.relative_to(ROOT)), errors)
            versions[(aid, v)] = vo
            if vo.get("asset_id") != aid or vo.get("version") != v:
                errors.append(f"{vp}: identity mismatch")
            if vo.get("parent_version") and vo["parent_version"] not in obj["versions"]:
                errors.append(f"{vp}: unknown parent")
            if vo.get("recipe") and not (ROOT / vo["recipe"]).is_file():
                errors.append(f"{vp}: missing recipe")
            elif vo.get("recipe"):
                if not vo.get("recipe_sha256"):
                    errors.append(f"{vp}: recipe hash missing")
                elif hashlib.sha256((ROOT / vo["recipe"]).read_bytes()).hexdigest() != vo["recipe_sha256"].lower():
                    errors.append(f"{vp}: recipe hash mismatch")
            elif vo.get("recipe_sha256"):
                errors.append(f"{vp}: recipe hash without recipe")
            for file in vo.get("artifacts", []):
                checked_file(file, f"{aid}/{v}", errors)
            params = vo.get("parameters", {})
            manifest = params.get("source_manifest") or params.get("baseline", {}).get("source_manifest")
            manifest_hash = params.get("source_manifest_sha256") or params.get("baseline", {}).get("source_manifest_sha256")
            if manifest and manifest_hash:
                checked_file({"path": manifest, "sha256": manifest_hash}, f"{aid}/{v} manifest", errors)
            if vo.get("status") == "approved":
                if not vo.get("artifacts") or not vo.get("runs") or vo.get("review", {}).get("decision") != "accepted" or not vo.get("review", {}).get("evidence"):
                    errors.append(f"{aid}/{v}: approved requires artifact, run and accepted review with evidence")
                required = vo.get("quality", {}).get("required", [])
                results = vo.get("quality", {}).get("results", [])
                passed = {x.get("gate") for x in results if x.get("result") == "pass" and x.get("evidence") and x.get("run_id") in vo.get("runs", [])}
                if not required or set(required) - passed:
                    errors.append(f"{aid}/{v}: approved requires passing evidence for all quality gates")
        if obj.get("current_version") not in obj.get("versions", []):
            errors.append(f"{aid}: current_version is not registered")
    for path in sorted((CATALOG / "runs").glob("*.json")):
        obj = read(path)
        validate_shape(obj, read(SCHEMAS / "run.schema.json"), str(path.relative_to(ROOT)), errors)
        rid = obj.get("run_id")
        runs[rid] = obj
        if path.stem != rid:
            errors.append(f"{path}: run ID/path mismatch")
        if (obj.get("asset_id"), obj.get("version")) not in versions:
            errors.append(f"{rid}: unknown asset/version")
        if obj.get("status") in ("completed", "failed", "cancelled") and not obj.get("finished_at"):
            errors.append(f"{rid}: terminal run needs finished_at")
        for ref in obj.get("inputs", []) + obj.get("outputs", []) + obj.get("lessons", []):
            checked_reference(ref, rid, errors)
    for (aid, v), vo in versions.items():
        for rid in vo.get("runs", []):
            if rid not in runs or (runs[rid]["asset_id"], runs[rid]["version"]) != (aid, v):
                errors.append(f"{aid}/{v}: broken run link {rid}")
        for dep in vo.get("dependencies", []):
            if dep not in assets:
                errors.append(f"{aid}/{v}: unknown dependency {dep}")
    for path in sorted((CATALOG / "assets").glob("*/*/versions/*.json")):
        vo = read(path)
        if (vo.get("asset_id"), vo.get("version")) not in versions:
            errors.append(f"{path.relative_to(ROOT)}: version file is not listed by its asset")
    for rid, run in runs.items():
        vo = versions.get((run["asset_id"], run["version"]))
        if vo and rid not in vo.get("runs", []):
            errors.append(f"{rid}: run is not linked from its version")
    for path in sorted((ROOT / "knowledge" / "lessons").glob("*.json")):
        obj = read(path)
        validate_shape(obj, read(SCHEMAS / "lesson.schema.json"), str(path.relative_to(ROOT)), errors)
        if path.stem != obj.get("id"):
            errors.append(f"{path}: lesson ID/path mismatch")
        for aid in obj.get("applies_to", []):
            if aid not in assets:
                errors.append(f"{path}: unknown asset {aid}")
        for ref in obj.get("evidence", []):
            checked_reference(ref, obj.get("id", str(path)), errors)
    vendor_manifest = ROOT / "vendor" / "mu-blender-addon" / "manifest.json"
    if vendor_manifest.is_file():
        for entry in read(vendor_manifest).get("files", []):
            checked_file({"path": "vendor/mu-blender-addon/" + entry["path"],
                          "sha256": entry["sha256"]}, "vendor addon", errors)
    print(f"{len(assets)} assets, {len(versions)} versions, {len(runs)} runs; {len(errors)} errors")
    for error in errors:
        print("ERROR", error)
    return not errors


def normalized(value):
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(c))


def list_assets(query=None):
    for path in sorted((CATALOG / "assets").glob("*/*/asset.json")):
        obj = read(path)
        haystack = " ".join([obj["id"], obj["name"], *obj.get("aliases", []), *obj.get("tags", [])])
        if query and normalized(query) not in normalized(haystack):
            continue
        print(f"{obj['id']}\t{obj['name']}\tcurrent={obj['current_version']}\tversions={','.join(obj['versions'])}")


def show(asset_id, selected=None):
    asset = read(asset_path(asset_id))
    selected = selected or asset["current_version"]
    version = read(version_path(asset_id, selected))
    summaries = [{"version": v, "status": read(version_path(asset_id, v))["status"]} for v in asset["versions"]]
    print(json.dumps({"asset": asset, "versions": summaries, "selected": version}, ensure_ascii=False, indent=2))


def new_asset(kind, slug, name, mu_id):
    allowed = read(SCHEMAS / "asset.schema.json")["properties"]["kind"]["enum"]
    if kind not in allowed:
        raise ValueError(f"unsupported kind: {kind}; choose from {', '.join(allowed)}")
    aid = f"mu:{kind}:{slug}"
    ap = asset_path(aid)
    if ap.exists():
        raise ValueError(f"already exists: {aid}")
    asset = {"schema_version": 1, "id": aid, "kind": kind, "slug": slug, "name": name,
             "mu_id": mu_id, "aliases": [], "current_version": "v0001", "versions": ["v0001"],
             "sources": [], "origin_hint": None, "references": [], "tags": []}
    version = {"schema_version": 1, "asset_id": aid, "version": "v0001", "status": "draft",
               "created_at": now(), "parent_version": None, "goal": "Document baseline and source files",
               "recipe": None, "recipe_sha256": None, "parameters": {}, "dependencies": [], "artifacts": [], "runs": [], "issues": [],
               "quality": {"required": [], "results": []},
               "review": {"decision": "pending", "by": None, "at": None, "evidence": [], "notes": ""}}
    write(ap, asset)
    write(version_path(aid, "v0001"), version)
    print(aid)


def new_version(aid, goal):
    ap = asset_path(aid)
    asset = read(ap)
    previous = asset["current_version"]
    v = f"v{max(int(x[1:]) for x in asset['versions']) + 1:04d}"
    base = read(version_path(aid, previous))
    recipe = base["recipe"]
    if recipe is None:
        proposed = {"monster": "monster-hd-v1", "npc": "monster-hd-v1", "character": "monster-hd-v1",
                    "item": "item-hd-v1", "world_prop": "world-prop-v1", "map": "world-prop-v1",
                    "effect": "world-prop-v1", "shader": "shader-modernize-v1", "material": "shader-modernize-v1"}
        name = proposed.get(aid.split(":")[1])
        recipe = f"recipes/{name}.json" if name else None
    version = {"schema_version": 1, "asset_id": aid, "version": v, "status": "draft",
               "created_at": now(), "parent_version": previous, "goal": goal,
               "recipe": recipe, "recipe_sha256": hashlib.sha256((ROOT / recipe).read_bytes()).hexdigest() if recipe else None,
               "parameters": {"inherited_from": previous,
                   "baseline": copy.deepcopy(base["parameters"]), "planned_overrides": {}},
               "dependencies": copy.deepcopy(base.get("dependencies", [])), "artifacts": [], "runs": [],
               "issues": [], "quality": {"required": [s["id"] for s in read(ROOT / recipe)["stages"]] if recipe else [], "results": []},
               "review": {"decision": "pending", "by": None, "at": None, "evidence": [], "notes": ""}}
    write(version_path(aid, v), version)
    asset["versions"].append(v)
    write(ap, asset)
    print(f"{aid}/{v} (parent {previous}); complete parameters before generating")


def new_run(aid, version, stage, goal, actor):
    if not re.fullmatch(r"[a-z0-9_-]+", stage):
        raise ValueError("stage must contain only lowercase letters, numbers, _ or -")
    vp = version_path(aid, version)
    vo = read(vp)
    if vo["status"] in ("approved", "rejected"):
        raise ValueError("start a new version before changing an approved/rejected result")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ").lower()
    rid = f"{aid.split(':')[-1]}-{version}-{stage}-{stamp}"
    rp = CATALOG / "runs" / (rid + ".json")
    if rp.exists():
        raise ValueError("run ID collision; retry later")
    obj = {"schema_version": 1, "run_id": rid, "asset_id": aid, "version": version,
           "stage": stage, "status": "planned", "started_at": now(), "finished_at": None,
           "goal": goal, "actor": actor, "environment": {}, "parameters": copy.deepcopy(vo["parameters"]),
           "inputs": [], "steps": [], "outputs": [], "observations": [], "checks": [], "lessons": []}
    write(rp, obj)
    vo.setdefault("runs", []).append(rid)
    write(vp, vo)
    print(rp.relative_to(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    p = sub.add_parser("list"); p.add_argument("--query")
    p = sub.add_parser("show"); p.add_argument("asset_id"); p.add_argument("--version")
    p = sub.add_parser("new-asset"); p.add_argument("kind"); p.add_argument("slug"); p.add_argument("name"); p.add_argument("--mu-id")
    p = sub.add_parser("new-version"); p.add_argument("asset_id"); p.add_argument("--goal", required=True)
    p = sub.add_parser("new-run"); p.add_argument("asset_id"); p.add_argument("version"); p.add_argument("--stage", required=True); p.add_argument("--goal", required=True); p.add_argument("--actor", default="unknown")
    args = parser.parse_args()
    if args.cmd == "validate":
        raise SystemExit(0 if validate() else 1)
    if args.cmd == "list": list_assets(args.query)
    if args.cmd == "show": show(args.asset_id, args.version)
    if args.cmd == "new-asset": new_asset(args.kind, args.slug, args.name, args.mu_id)
    if args.cmd == "new-version": new_version(args.asset_id, args.goal)
    if args.cmd == "new-run": new_run(args.asset_id, args.version, args.stage, args.goal, args.actor)


if __name__ == "__main__":
    main()

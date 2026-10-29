"""One-command, profile-driven monster build with provenance and quality gates.

Example: py -3.9 tools/monster_engine.py build profiles/monster03.json

A profile supplies the asset-specific builder. The engine never labels a model
complete from a technical scan alone; it records pending visual/game gates.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLENDER_DEFAULT = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")


def rel(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f"Outside project: {path}")
    return path.relative_to(ROOT).as_posix()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def invoke(blender, scene, script, args, log, env=None):
    command = [str(blender), "-b", str(scene), "-t", "4", "--python", str(script)]
    if args:
        command.extend(["--", *map(str, args)])
    proc = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, errors="replace",
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=900)
    log.write_text(proc.stdout, encoding="utf-8")
    if proc.returncode != 0 or "Traceback (most recent call last)" in proc.stdout:
        raise RuntimeError(f"Blender stage failed; see {rel(log)}")
    return command


def build(profile_path, blender):
    profile_path = (ROOT / profile_path).resolve()
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    aid = profile["asset_id"]
    version = profile["version"]
    slug = aid.split(":")[-1]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{slug}-{version}-engine-{timestamp}".lower()
    assert re.fullmatch(r"[a-z0-9_-]+", run_id)
    folder = ROOT / "work" / slug / "engine-runs" / run_id
    folder.mkdir(parents=True, exist_ok=False)
    source = ROOT / profile["source_scene"]
    builder = ROOT / profile["builder_script"]
    candidate = folder / profile["candidate_scene_name"]
    audit_script = ROOT / "tools" / "audit_monster_scene.py"
    render_script = ROOT / profile["render_script"]
    compose_script = ROOT / profile["compose_script"]
    audit = folder / "audit.json"
    poses = folder / "poses"
    start = datetime.now(timezone.utc).isoformat(timespec="seconds")
    env = os.environ.copy()
    env["MU_ASSET_OUTPUT"] = str(candidate)
    build_command = invoke(blender, source, builder, [], folder / "build.log", env)
    if not candidate.is_file():
        raise RuntimeError(f"Builder did not produce {candidate}")
    audit_command = invoke(blender, candidate, audit_script,
                           [rel(profile_path), str(audit)], folder / "audit.log")
    if not audit.is_file():
        raise RuntimeError("Audit did not produce a report")
    render_command = invoke(blender, candidate, render_script,
                            [rel(profile_path), str(poses)], folder / "render.log")
    compose_command = [sys.executable, str(compose_script), str(poses)]
    compose_result = subprocess.run(compose_command, cwd=ROOT, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, errors="replace",
                                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=120)
    (folder / "compose.log").write_text(compose_result.stdout, encoding="utf-8")
    if compose_result.returncode or not (poses / "full-body-actions.png").is_file():
        raise RuntimeError(f"Pose-sheet composition failed; see {rel(folder / 'compose.log')}")
    quality = json.loads(audit.read_text(encoding="utf-8"))
    hashes = {rel(path): digest(path) for path in
              (profile_path, source, builder, audit_script, render_script, compose_script,
               candidate, audit, poses / "full-body-actions.png")}
    provenance = folder / "provenance.json"
    save(provenance, {"run_id": run_id, "asset_id": aid, "version": version,
                      "hashes_sha256": hashes, "build_command": build_command,
                      "audit_command": audit_command, "render_command": render_command,
                      "compose_command": compose_command,
                      "release_status": quality["release_status"]})

    run = {
        "schema_version": 1, "run_id": run_id, "asset_id": aid, "version": version,
        "stage": "geometry", "status": "completed", "started_at": start,
        "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "goal": "Build and audit a complete monster candidate from a reproducible asset profile",
        "actor": "monster_engine.py",
        "environment": {"blender": str(blender), "python": sys.version.split()[0]},
        "parameters": {"profile": rel(profile_path), "profile_sha256": hashes[rel(profile_path)],
                       "builder": rel(builder), "candidate_sha256": hashes[rel(candidate)],
                       "release_status": quality["release_status"]},
        "inputs": [rel(source), rel(profile_path), rel(builder)],
        "steps": ["Run asset-specific Blender builder", "Audit LODs, UVs, materials, weights, regions and every action frame", "Render full-body action pose sheet", "Record hashes and quality gates"],
        "outputs": [rel(candidate), rel(audit), rel(poses / "full-body-actions.png"), rel(poses / "frames.json"),
                    rel(provenance), rel(folder / "build.log"), rel(folder / "audit.log"),
                    rel(folder / "render.log"), rel(folder / "compose.log")],
        "observations": ["A built candidate is not automatically approved.",
                         "Pending human gates: " + ", ".join(quality["pending_human_gates"])],
        "checks": [{"name": item["name"], "result": item["result"], "evidence": rel(audit)} for item in quality["checks"]]
                  + [{"name": "release", "result": "manual", "evidence": rel(audit)}],
    }
    run_path = ROOT / "catalog" / "runs" / f"{run_id}.json"
    save(run_path, run)
    version_path = ROOT / "catalog" / "assets" / "monster" / slug / "versions" / f"{version}.json"
    record = json.loads(version_path.read_text(encoding="utf-8"))
    if run_id not in record["runs"]:
        record["runs"].append(run_id)
    save(version_path, record)
    print(json.dumps({"run_id": run_id, "candidate": rel(candidate),
                      "audit": rel(audit), "pose_sheet": rel(poses / "full-body-actions.png"),
                      "release_status": quality["release_status"],
                      "technical_failures": quality["technical_failures"]}, ensure_ascii=False))
    return 0 if quality["release_status"] == "eligible_for_review" else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build"])
    parser.add_argument("profile")
    parser.add_argument("--blender", type=Path, default=BLENDER_DEFAULT)
    options = parser.parse_args()
    sys.exit(build(options.profile, options.blender))

"""MU Asset Lab — Orquestrador Unificado do Pipeline de Modernização

Ponto de entrada central para agentes de IA e desenvolvedores.
Executa e valida cada estágio do pipeline de forma determinística e reproduzível.

Comandos:
  py -3.9 tools/run_pipeline.py doctor
  py -3.9 tools/run_pipeline.py textures
  py -3.9 tools/run_pipeline.py baseline --profile profiles/monster03.json
  py -3.9 tools/run_pipeline.py mouth --scene work/monster03/budge-dragon-baseline-v2.blend
  py -3.9 tools/run_pipeline.py build --profile profiles/monster03.json
  py -3.9 tools/run_pipeline.py validate --profile profiles/monster03.json
  py -3.9 tools/run_pipeline.py all --profile profiles/monster03.json
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def get_blender_binary():
    env_bin = os.environ.get("BLENDER_PATH") or os.environ.get("BLENDER_BIN")
    if env_bin and Path(env_bin).is_file():
        return Path(env_bin)
    which_bin = shutil.which("blender")
    if which_bin:
        return Path(which_bin)
    for ver in ["5.2", "5.1", "5.0", "4.3", "4.2", "4.1", "4.0", "3.6"]:
        cand = Path(rf"C:\Program Files\Blender Foundation\Blender {ver}\blender.exe")
        if cand.is_file():
            return cand
    mac_bin = Path("/Applications/Blender.app/Contents/MacOS/Blender")
    if mac_bin.is_file():
        return mac_bin
    return Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")


def run_command(cmd, desc=""):
    print(f"\n[Pipeline] >>> {desc or 'Executando'}: {' '.join(str(c) for c in cmd)}")
    res = subprocess.run(cmd, cwd=ROOT, text=True)
    if res.returncode != 0:
        print(f"[Pipeline] [ERRO] Falha no comando (código {res.returncode}): {' '.join(str(c) for c in cmd)}")
        return False
    return True


def doctor():
    print("==================================================")
    print("      MU Asset Lab — Verificação de Ambiente      ")
    print("==================================================")
    python_ver = sys.version.split()[0]
    print(f"  [+] Python runtime: {python_ver} ({sys.executable})")

    blender_path = get_blender_binary()
    if blender_path.is_file():
        print(f"  [+] Blender executável: {blender_path} (Encontrado)")
    else:
        print(f"  [!] Blender executável: {blender_path} (Aviso: não detectado neste caminho padrão; defina BLENDER_PATH se necessário)")

    # Teste de integridade do registro
    print("\n[+] Validando integridade do repositório via tools/registry.py...")
    reg_script = ROOT / "tools" / "registry.py"
    res = subprocess.run([sys.executable, str(reg_script), "validate"], cwd=ROOT, text=True)
    if res.returncode == 0:
        print("  [OK] Registro de assets 100% íntegro (0 erros).")
        return True
    else:
        print("  [ERRO] Falhas encontradas no registro.")
        return False


def run_textures():
    script = ROOT / "tools" / "decode_legacy_textures.py"
    return run_command([sys.executable, str(script)], "Decodificando texturas legadas (OZJ/OZT)")


def run_baseline(blender_bin):
    script = ROOT / "tools" / "prepare_dragon_baseline.py"
    return run_command([str(blender_bin), "-b", "--python", str(script)], "Construindo cena baseline de referência no Blender")


def run_mouth(blender_bin, scene_path):
    script = ROOT / "tools" / "build_hd_mouth_rig.py"
    scene = scene_path or (ROOT / "work" / "monster03" / "budge-dragon-baseline-v2.blend")
    return run_command([str(blender_bin), str(scene), "-b", "--python", str(script)], "Construindo geometria anatômica MOUTH_UPPER e MOUTH_LOWER")


def run_build(blender_bin, profile_path):
    engine_script = ROOT / "tools" / "monster_engine.py"
    prof = profile_path or (ROOT / "profiles" / "monster03.json")
    return run_command([sys.executable, str(engine_script), "build", str(prof), "--blender", str(blender_bin)], "Executando Monster Engine build")


def run_validate(blender_bin, profile_path):
    prof = profile_path or (ROOT / "profiles" / "monster03.json")
    candidate = ROOT / "work" / "monster03" / "candidate.blend"
    if not candidate.is_file():
        candidate = ROOT / "work" / "monster03" / "candidate-mouth-rig.blend"
    report = ROOT / "work" / "monster03" / "rig-validation.json"

    ok = True
    if candidate.is_file():
        ok = run_command([
            str(blender_bin), str(candidate), "-b", "--python-exit-code", "1",
            "--python", str(val_script), "--",
            "--profile", str(prof),
            "--report", str(report),
            "--upper-mesh", "MOUTH_UPPER",
            "--lower-mesh", "MOUTH_LOWER"
        ], "Validando simetria facial, limites de pesos e abertura de boca sem colisão")

    # Sempre roda registry validate
    reg_script = ROOT / "tools" / "registry.py"
    ok_reg = run_command([sys.executable, str(reg_script), "validate"], "Validando integridade do catálogo e histórico")
    return ok and ok_reg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["doctor", "textures", "baseline", "mouth", "build", "validate", "all"])
    parser.add_argument("--profile", type=Path, default=ROOT / "profiles" / "monster03.json")
    parser.add_argument("--scene", type=Path, default=None)
    parser.add_argument("--blender", type=Path, default=None)
    args = parser.parse_args()

    blender_bin = args.blender or get_blender_binary()

    if args.stage == "doctor":
        sys.exit(0 if doctor() else 1)
    elif args.stage == "textures":
        sys.exit(0 if run_textures() else 1)
    elif args.stage == "baseline":
        run_textures()
        sys.exit(0 if run_baseline(blender_bin) else 1)
    elif args.stage == "mouth":
        sys.exit(0 if run_mouth(blender_bin, args.scene) else 1)
    elif args.stage == "build":
        sys.exit(0 if run_build(blender_bin, args.profile) else 1)
    elif args.stage == "validate":
        sys.exit(0 if run_validate(blender_bin, args.profile) else 1)
    elif args.stage == "all":
        print("\n>>> INICIANDO EXECUÇÃO COMPLETA DO PIPELINE <<<")
        if not doctor():
            print("[ERRO] Doctor reportou problemas. Verifique antes de continuar.")
        run_textures()
        run_baseline(blender_bin)
        run_mouth(blender_bin, args.scene)
        run_build(blender_bin, args.profile)
        run_validate(blender_bin, args.profile)
        print("\n>>> PIPELINE FINALIZADO <<<")


if __name__ == "__main__":
    main()

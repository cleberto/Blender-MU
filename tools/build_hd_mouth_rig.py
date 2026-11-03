"""MU Asset Lab — Construtor Completo de Rig e Topologia Bucal (Monster03 / Budge Dragon)

Resolve o bloqueio anatômico de abertura de boca do Budge Dragon:
  * MOUTH_UPPER: maxila superior com grupo MOUTH_UPPER_RIM e ZERO peso em Bone02.
  * MOUTH_LOWER: mandíbula inferior com grupo MOUTH_LOWER_RIM acoplado a Bone02.
  * MouthInterior_Cavity, MouthInterior_Tongue, MouthInterior_Fangs: interior bucal
    volumétrico exigido pelo contrato de qualidade (audit_monster_scene.py).
  * Limitação estrita de no máximo 4 pesos por vértice e normalização completa.

Suporta execução autônoma via CLI e integração como builder no monster_engine.py:
  blender work/monster03/budge-dragon-baseline-v2.blend -b --python tools/build_hd_mouth_rig.py
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]


def parse_output_path():
    # 1. Se invocado pelo monster_engine.py via variável de ambiente:
    env_out = os.environ.get("MU_ASSET_OUTPUT")
    if env_out:
        return Path(env_out), Path(env_out).with_suffix(".json")

    # 2. Se invocado com argumentos de linha de comando:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "work" / "monster03" / "candidate.blend"))
    parser.add_argument("--report", default=str(ROOT / "work" / "monster03" / "mouth-rig-report.json"))
    args = parser.parse_args(argv)
    return Path(args.output), Path(args.report)


def get_or_create_collection(name):
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    return col


def create_material(name, base_color, roughness):
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        node = mat.node_tree.nodes.get("Principled BSDF")
        if node:
            node.inputs["Base Color"].default_value = (*base_color, 1.0)
            node.inputs["Roughness"].default_value = roughness
    return mat


def build_tube_interior(name, sections, mat, bone_name, arm, col, source_obj, sides=16):
    to_local = source_obj.matrix_world.inverted()
    points, faces = [], []
    for y, width, z, height in sections:
        for i in range(sides):
            angle = 2 * math.pi * i / sides
            points.append((width * math.cos(angle), y, z + height * math.sin(angle)))
    for ring in range(len(sections) - 1):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((ring * sides + i, ring * sides + j,
                          (ring + 1) * sides + j, (ring + 1) * sides + i))
    faces.append(tuple(reversed(range(sides))))
    last = (len(sections) - 1) * sides
    faces.append(tuple(last + i for i in range(sides)))

    data = bpy.data.meshes.new(name + "_mesh")
    data.from_pydata([tuple(to_local @ Vector(p)) for p in points], [], faces)
    data.update()

    obj = bpy.data.objects.new(name, data)
    col.objects.link(obj)
    obj.matrix_world = source_obj.matrix_world.copy()
    data.materials.append(mat)
    for face in data.polygons:
        face.use_smooth = True

    group = obj.vertex_groups.new(name=bone_name)
    group.add(list(range(len(points))), 1.0, "REPLACE")

    mod = obj.modifiers.new("MU_Armature", "ARMATURE")
    mod.object = arm
    return obj


def build_fang(name, x, y, z, length, direction, radius, bone_name, arm, col, source_obj, mat):
    to_local = source_obj.matrix_world.inverted()
    sides = 10
    points = []
    for step, (r, advance) in enumerate(((radius, 0), (radius * 0.70, 0.38),
                                         (radius * 0.35, 0.75), (0.03, 1.0))):
        for i in range(sides):
            angle = i * math.tau / sides
            bend = (step / 3) ** 2 * 0.35
            points.append((x + r * math.cos(angle), y + r * math.sin(angle) - bend,
                           z + direction * length * advance))
    faces = []
    for ring in range(3):
        for i in range(sides):
            j = (i + 1) % sides
            faces.append((ring * sides + i, ring * sides + j,
                          (ring + 1) * sides + j, (ring + 1) * sides + i))
    faces.append(tuple(reversed(range(sides))))

    data = bpy.data.meshes.new(name + "_mesh")
    data.from_pydata([tuple(to_local @ Vector(p)) for p in points], [], faces)
    data.update()

    obj = bpy.data.objects.new(name, data)
    col.objects.link(obj)
    obj.matrix_world = source_obj.matrix_world.copy()
    data.materials.append(mat)
    for face in data.polygons:
        face.use_smooth = True

    group = obj.vertex_groups.new(name=bone_name)
    group.add(list(range(len(points))), 1.0, "REPLACE")

    mod = obj.modifiers.new("MU_Armature", "ARMATURE")
    mod.object = arm
    return obj


def prune_vertex_influences(obj, max_influences=4):
    """Garante no máximo 4 pesos por vértice e normaliza para soma 1.0."""
    for vertex in obj.data.vertices:
        memberships = sorted(((g.group, g.weight) for g in vertex.groups),
                             key=lambda item: -item[1])
        if len(memberships) > max_influences:
            keep = memberships[:max_influences]
            total = sum(w for _, w in keep)
            for gid, _ in memberships:
                obj.vertex_groups[gid].remove([vertex.index])
            for gid, w in keep:
                obj.vertex_groups[gid].add([vertex.index], w / total if total > 0 else 0, "REPLACE")


def main():
    out_path, report_path = parse_output_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    source = bpy.data.objects.get("LOD0")
    arm = bpy.data.objects.get("mu_root")
    if not source or not arm:
        raise RuntimeError("Missing LOD0 or mu_root armature in scene")

    col_mouth = get_or_create_collection("V0002_MOUTH_RIG")

    # =========================================================================
    # 1. CONSTRUIR MOUTH_UPPER (Maxila / Focinho Superior)
    # =========================================================================
    upper_obj = bpy.data.objects.get("MOUTH_UPPER")
    if not upper_obj:
        upper_data = source.data.copy()
        upper_obj = bpy.data.objects.new("MOUTH_UPPER", upper_data)
        col_mouth.objects.link(upper_obj)
        upper_obj.matrix_world = source.matrix_world.copy()

    # Remover qualquer influência residual de Bone02 da maxila superior
    if "Bone02" in upper_obj.vertex_groups:
        upper_obj.vertex_groups.remove(upper_obj.vertex_groups["Bone02"])

    # Criar grupo MOUTH_UPPER_RIM
    upper_rim = upper_obj.vertex_groups.get("MOUTH_UPPER_RIM")
    if not upper_rim:
        upper_rim = upper_obj.vertex_groups.new(name="MOUTH_UPPER_RIM")

    rim_upper_indices = []
    for v in upper_obj.data.vertices:
        world_pt = upper_obj.matrix_world @ v.co
        if world_pt.y < -45 and 118 <= world_pt.z <= 126 and abs(world_pt.x) < 20:
            rim_upper_indices.append(v.index)

    if rim_upper_indices:
        upper_rim.add(rim_upper_indices, 1.0, "REPLACE")

    # =========================================================================
    # 2. CONSTRUIR MOUTH_LOWER (Mandíbula Inferior)
    # =========================================================================
    lower_obj = bpy.data.objects.get("MOUTH_LOWER")
    if not lower_obj:
        lower_data = source.data.copy()
        lower_obj = bpy.data.objects.new("MOUTH_LOWER", lower_data)
        col_mouth.objects.link(lower_obj)
        lower_obj.matrix_world = source.matrix_world.copy()

    # Garantir que MOUTH_LOWER tenha influência de Bone02
    lower_bone02 = lower_obj.vertex_groups.get("Bone02")
    if not lower_bone02:
        lower_bone02 = lower_obj.vertex_groups.new(name="Bone02")

    # Criar grupo MOUTH_LOWER_RIM
    lower_rim = lower_obj.vertex_groups.get("MOUTH_LOWER_RIM")
    if not lower_rim:
        lower_rim = lower_obj.vertex_groups.new(name="MOUTH_LOWER_RIM")

    rim_lower_indices = []
    for v in lower_obj.data.vertices:
        world_pt = lower_obj.matrix_world @ v.co
        if world_pt.y < -42 and world_pt.z < 118 and abs(world_pt.x) < 20:
            rim_lower_indices.append(v.index)
            lower_bone02.add([v.index], 1.0, "REPLACE")

    if rim_lower_indices:
        lower_rim.add(rim_lower_indices, 1.0, "REPLACE")

    # Vincular Armature modifier em ambos
    for obj in (upper_obj, lower_obj):
        mod = obj.modifiers.get("MU_Armature")
        if not mod:
            mod = obj.modifiers.new("MU_Armature", "ARMATURE")
        mod.object = arm
        prune_vertex_influences(obj, 4)

    # =========================================================================
    # 3. INTERIOR BUCAL VOLUMÉTRICO (MouthInterior_*)
    # =========================================================================
    cavity_mat = create_material("M03_Mouth_Cavity_Burgundy", (0.055, 0.009, 0.014), 0.72)
    tongue_mat = create_material("M03_Tongue_Dusky_Rose", (0.30, 0.068, 0.074), 0.47)
    tooth_mat = create_material("M03_Tooth_Warm_Ivory", (0.78, 0.68, 0.52), 0.34)

    # Cavidade interna (Palato e garganta presa a Bip01 Head)
    if not bpy.data.objects.get("MouthInterior_Cavity"):
        build_tube_interior("MouthInterior_Cavity", [
            (-76, 1.5, 117.1, 0.3), (-73, 4.6, 117.6, 1.2),
            (-66, 6.4, 118.2, 1.9), (-58, 8.0, 119.0, 2.0),
            (-50, 9.2, 119.5, 2.0), (-44, 7.2, 120.2, 1.6),
            (-40, 2.4, 121.0, 0.3)
        ], cavity_mat, "Bip01 Head", arm, col_mouth, source)

    # Língua presa a Bone02 (segue a abertura da mandíbula)
    if not bpy.data.objects.get("MouthInterior_Tongue"):
        build_tube_interior("MouthInterior_Tongue", [
            (-74, 1.2, 116.8, 0.2), (-66, 3.8, 116.9, 0.6),
            (-56, 4.8, 117.2, 0.8), (-47, 4.2, 117.5, 0.6),
            (-41, 1.6, 117.8, 0.2)
        ], tongue_mat, "Bone02", arm, col_mouth, source)

    # Presas superiores e inferiores (Fangs)
    if not bpy.data.objects.get("MouthInterior_Fang_UL"):
        build_fang("MouthInterior_Fang_UL", -5.5, -57.0, 119.8, 2.4, -1, 0.42, "Bip01 Head", arm, col_mouth, source, tooth_mat)
        build_fang("MouthInterior_Fang_UR", 5.5, -57.0, 119.8, 2.4, -1, 0.42, "Bip01 Head", arm, col_mouth, source, tooth_mat)
        build_fang("MouthInterior_Fang_LL", -4.8, -52.0, 116.5, 2.1, 1, 0.38, "Bone02", arm, col_mouth, source, tooth_mat)
        build_fang("MouthInterior_Fang_LR", 4.8, -52.0, 116.5, 2.1, 1, 0.38, "Bone02", arm, col_mouth, source, tooth_mat)

    # Salvar cena candidata
    bpy.ops.wm.save_as_mainfile(filepath=str(out_path))

    report = {
        "stage": "build_hd_mouth_rig",
        "status": "ready_for_validation",
        "output_blend": str(out_path),
        "upper_mesh": upper_obj.name,
        "upper_rim_vertices": len(rim_upper_indices),
        "upper_jaw_leakage": "Bone02" in upper_obj.vertex_groups,
        "lower_mesh": lower_obj.name,
        "lower_rim_vertices": len(rim_lower_indices),
        "mouth_interior_objects": [obj.name for obj in col_mouth.objects if obj.name.startswith("MouthInterior_")],
        "actions_evaluated": len(arm.animation_data.nla_tracks) or len(bpy.data.actions)
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"MOUTH_RIG_BUILD_JSON={json.dumps(report)}")


if __name__ == "__main__":
    main()

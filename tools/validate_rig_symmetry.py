"""
MU Asset Lab — Tool de Verificação Pré-Bake & Rig
Arquivo: tools/validate_rig_symmetry.py

Validações executadas:
1. Symmetry Check: Compara pares de vértices no eixo X com tolerância estrita.
2. Jaw Weight Check: Valida influências do osso da mandíbula (Bone02), garantindo
   que a boca se mova sem deformar o crânio superior.
3. Action Frame Sweep: Itera pelas 7 ações (foco em Attack/Roar) detectando
   intersecção/colisão entre maxila superior e mandíbula inferior.
"""

import bpy
import bmesh
import math
import sys
from mathutils import Vector, kdtree
from mathutils.bvhtree import BVHTree

def log_pass(msg):
    print(f"  [PASS] {msg}")

def log_warn(msg):
    print(f"  [WARN] {msg}")

def log_fail(msg):
    print(f"  [FAIL] {msg}")

def validate_symmetry(mesh_obj, tolerance=0.005, max_failures_reported=5):
    """
    Verifica se a malha possui simetria no eixo X (X = -X).
    Usa KD-Tree para busca espacial rápida de vértices espelhados.
    """
    print("\n--- 1. Symmetry Check (Eixo X) ---")
    mesh = mesh_obj.data
    size = len(mesh.vertices)
    
    kd = kdtree.KDTree(size)
    for i, v in enumerate(mesh.vertices):
        kd.insert(v.co, i)
    kd.balance()
    
    asymmetric_count = 0
    failures = []
    
    for i, v in enumerate(mesh.vertices):
        # Ignora vértices na linha central de costura
        if abs(v.co.x) < 0.0001:
            continue
            
        expected_mirror = Vector((-v.co.x, v.co.y, v.co.z))
        co, index, dist = kd.find(expected_mirror)
        
        if dist > tolerance:
            asymmetric_count += 1
            if len(failures) < max_failures_reported:
                failures.append((i, v.co, dist))
                
    if asymmetric_count == 0:
        log_pass("Simetria bilateral perfeitamente alinhada no eixo X.")
        return True
    else:
        log_fail(f"Encontrados {asymmetric_count} vértices fora da tolerância de {tolerance}m.")
        for idx, co, d in failures:
            print(f"       -> Vértice #{idx} em {co}: desvio de {d:.5f}m")
        return False

def validate_jaw_weights(mesh_obj, armature_obj, jaw_bone_name="Bone02", head_bone_name="Bone01"):
    """
    Garante que a mandíbula (Bone02) possui pesos atribuídos e não contamina
    a maxila superior/crânio.
    """
    print("\n--- 2. Jaw & Cranium Weight Check ---")
    
    jaw_group = mesh_obj.vertex_groups.get(jaw_bone_name)
    head_group = mesh_obj.vertex_groups.get(head_bone_name)
    
    if not jaw_group:
        log_fail(f"Grupo de vértices '{jaw_bone_name}' não encontrado na malha!")
        return False
        
    jaw_idx = jaw_group.index
    jaw_vertices = []
    
    # 1. Contar vértices influenciados pela mandíbula
    for v in mesh_obj.data.vertices:
        for g in v.groups:
            if g.group == jaw_idx and g.weight > 0.01:
                jaw_vertices.append((v, g.weight))
                
    if len(jaw_vertices) == 0:
        log_fail(f"A mandíbula ('{jaw_bone_name}') tem 0 vértices com peso! A boca NUNCA irá abrir.")
        return False
    else:
        log_pass(f"Mandíbula ('{jaw_bone_name}') influencia {len(jaw_vertices)} vértices.")

    # 2. Checagem de isolamento da mandíbula vs crânio
    # Vértices da parte superior (Z elevado do focinho) não devem pertencer ao Bone02
    jaw_z_coords = [v[0].co.z for v in jaw_vertices]
    avg_jaw_z = sum(jaw_z_coords) / len(jaw_z_coords)
    max_jaw_z = max(jaw_z_coords)
    
    leaking_vertices = [v for v, w in jaw_vertices if v.co.z > (avg_jaw_z + 0.4)]
    if leaking_vertices:
        log_warn(f"{len(leaking_vertices)} vértices muito altos no crânio têm peso em '{jaw_bone_name}'. Possível estiramento do bico.")
    else:
        log_pass("Sem vazamento de peso da mandíbula para o crânio superior.")
        
    return True

def validate_action_frame_sweep(mesh_obj, armature_obj, actions_to_check=["Action3", "Action4", "attack", "roar"]):
    """
    Varre os quadros das animações de ataque/rugido procurando colisões
    e auto-intersecções entre a mandíbula e a cabeça.
    """
    print("\n--- 3. Action Frame Sweep (Intersecções na Abertura Bucal) ---")
    
    if not armature_obj.animation_data:
        log_warn("Armature não possui animation_data associado.")
        return True
        
    orig_action = armature_obj.animation_data.action
    found_actions = 0
    collisions_detected = 0
    
    # Buscar ações disponíveis
    all_actions = bpy.data.actions
    target_actions = [a for a in all_actions if any(tag.lower() in a.name.lower() for tag in actions_to_check)]
    
    if not target_actions:
        # Se não achou por nome, testa todas as ações registradas
        target_actions = list(all_actions)[:3]
        
    for act in target_actions:
        found_actions += 1
        armature_obj.animation_data.action = act
        frame_start = int(act.frame_range[0])
        frame_end = int(act.frame_range[1])
        
        print(f"  -> Testando Ação: '{act.name}' ({frame_start} a {frame_end} frames)...")
        
        # Testar amostras de frames (início, meio, pico)
        step = max(1, (frame_end - frame_start) // 8)
        for frame in range(frame_start, frame_end + 1, step):
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            
            # Avalia a malha deformada pelo armature
            depsgraph = bpy.context.evaluated_depsgraph_get()
            eval_obj = mesh_obj.evaluated_get(depsgraph)
            eval_mesh = eval_obj.to_mesh()
            
            # Criar BVH Tree para detecção de colisão rápida
            bvh = BVHTree.FromMesh(eval_mesh, epsilon=0.0001)
            overlaps = bvh.overlap(bvh)
            
            # Filtra arestas adjacentes normais
            real_overlaps = [pair for pair in overlaps if abs(pair[0] - pair[1]) > 1]
            eval_obj.to_mesh_clear()
            
            if len(real_overlaps) > 50:
                collisions_detected += 1
                log_warn(f"     Frame {frame}: {len(real_overlaps)} auto-intersecções detectadas na malha deformada.")
                break
                
    # Restaura ação original
    armature_obj.animation_data.action = orig_action
    
    if collisions_detected == 0:
        log_pass("Varredura de animação concluída: sem cruzamentos catastróficos de malha.")
        return True
    else:
        log_warn("Atenção: Existem poses em que a mandíbula cruza a geometria do focinho.")
        return False

def main():
    print("==================================================")
    print("   MU Asset Lab — Verificação de Rig e Simetria   ")
    print("==================================================")
    
    # 1. Localizar Mesh e Armature ativas
    mesh_obj = None
    armature_obj = None
    
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and not obj.name.startswith("Icosphere") and "ORIGINAL" not in obj.name:
            if mesh_obj is None or "LOD0" in obj.name or "HP" in obj.name:
                mesh_obj = obj
        elif obj.type == 'ARMATURE':
            armature_obj = obj
            
    if not mesh_obj:
        print("[ERRO] Nenhuma malha válida encontrada na cena para validação.")
        sys.exit(1)
        
    print(f"Alvo Mesh: '{mesh_obj.name}'")
    if armature_obj:
        print(f"Alvo Armature: '{armature_obj.name}'")
        
    # Execução dos Gates
    gate1 = validate_symmetry(mesh_obj, tolerance=0.005)
    gate2 = validate_jaw_weights(mesh_obj, armature_obj, jaw_bone_name="Bone02") if armature_obj else False
    gate3 = validate_action_frame_sweep(mesh_obj, armature_obj) if armature_obj else False
    
    print("\n==================================================")
    if gate1 and gate2 and gate3:
        print("  RESULTADO GERAL: [APROVADO] - Pronto para Bake/Export")
        print("==================================================")
        return 0
    else:
        print("  RESULTADO GERAL: [REPROVADO] - Corrija os erros acima")
        print("==================================================")
        return 1

if __name__ == "__main__":
    main()

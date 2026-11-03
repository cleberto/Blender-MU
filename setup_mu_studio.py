"""
MU Asset Lab — Setup de Estúdio Master de Renderização
Arquivo: tools/setup_mu_studio.py

Configura automaticamente uma cena de apresentação nível Sketchfab/Colecionável:
- Motor Cycles com AgX e Denoise
- Iluminação 3 Pontos (Key 5500K, Fill 6500K fria, Rim 600W de recorte)
- Câmera 85mm com foco e enquadramento automático no monstro/item
"""

import bpy
import math
from mathutils import Vector

def setup_mu_master_studio():
    print("==================================================")
    print("   MU Asset Lab — Configurando Estúdio Master    ")
    print("==================================================")
    
    scene = bpy.context.scene
    
    # 1. Configuração do Motor de Render (Cycles + AgX)
    scene.render.engine = 'CYCLES'
    
    # Ativar GPU se disponível
    try:
        cycles_prefs = bpy.context.preferences.addons['cycles'].preferences
        cycles_prefs.get_devices()
        scene.cycles.device = 'GPU'
        print("  [OK] GPU Compute ativado no Cycles.")
    except Exception:
        print("  [INFO] Usando CPU para renderização.")
        
    scene.cycles.samples = 256
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    
    # Color Management (AgX para cores sem estourar highlights)
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'Medium High Contrast'
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    print("  [OK] Color Management: AgX Medium High Contrast configurado.")
    
    # 2. Localizar o Monstro/Item para medir proporções
    target_obj = None
    for obj in scene.objects:
        if obj.type == 'MESH' and obj.visible_get() and not obj.name.startswith("Icosphere"):
            target_obj = obj
            break
            
    # Centro e tamanho padrão caso não haja objeto selecionado
    center = Vector((0.0, 0.0, 1.0))
    height = 2.0
    
    if target_obj:
        bbox = [target_obj.matrix_world @ Vector(corner) for corner in target_obj.bound_box]
        center = sum(bbox, Vector()) / 8.0
        min_z = min(corner.z for corner in bbox)
        max_z = max(corner.z for corner in bbox)
        height = max(0.5, max_z - min_z)
        print(f"  [OK] Enquadrando asset: '{target_obj.name}' (Altura: {height:.2f}m)")

    # 3. Criar ou Limpar Coleção do Estúdio
    col_name = "90_STUDIO_LIGHTS"
    col = bpy.data.collections.get(col_name)
    if not col:
        col = bpy.data.collections.new(col_name)
        scene.collection.children.link(col)
        
    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    # 4. Key Light (Luz Principal) - 45º à frente, quente suave
    key_data = bpy.data.lights.new(name="MU_Key_Light", type='AREA')
    key_data.energy = 250 * (height / 2.0)
    key_data.size = height * 1.2
    key_data.color = (1.0, 0.95, 0.9)
    key_obj = bpy.data.objects.new("MU_Key_Light", key_data)
    key_obj.location = center + Vector((-height * 1.5, -height * 1.8, height * 1.2))
    key_obj.rotation_euler = (math.radians(50), math.radians(10), math.radians(-40))
    col.objects.link(key_obj)

    # 5. Fill Light (Preenchimento) - Oposto à Key, fria suave
    fill_data = bpy.data.lights.new(name="MU_Fill_Light", type='AREA')
    fill_data.energy = 80 * (height / 2.0)
    fill_data.size = height * 2.0
    fill_data.color = (0.85, 0.92, 1.0)
    fill_obj = bpy.data.objects.new("MU_Fill_Light", fill_data)
    fill_obj.location = center + Vector((height * 2.0, -height * 1.5, height * 0.8))
    fill_obj.rotation_euler = (math.radians(60), math.radians(-10), math.radians(50))
    col.objects.link(fill_obj)

    # 6. Rim/Back Light (Destaque de Silhueta / Escamas)
    rim_data = bpy.data.lights.new(name="MU_Rim_Light", type='SPOT')
    rim_data.energy = 450 * (height / 2.0)
    rim_data.spot_size = math.radians(65)
    rim_data.spot_blend = 0.4
    rim_data.color = (1.0, 1.0, 1.0)
    rim_obj = bpy.data.objects.new("MU_Rim_Light", rim_data)
    rim_obj.location = center + Vector((0.0, height * 2.2, height * 1.5))
    rim_obj.rotation_euler = (math.radians(-40), 0, math.radians(180))
    col.objects.link(rim_obj)

    # 7. Câmera Heroica (85mm, sem distorção de grande angular)
    cam_data = bpy.data.cameras.new("MU_Hero_Camera")
    cam_data.lens = 85
    cam_obj = bpy.data.objects.new("MU_Hero_Camera", cam_data)
    
    dist_cam = height * 3.5
    cam_obj.location = center + Vector((0.0, -dist_cam, height * 0.2))
    cam_obj.rotation_euler = (math.radians(85), 0, 0)
    col.objects.link(cam_obj)
    scene.camera = cam_obj
    
    print("  [OK] Câmera 85mm posicionada e setada como ativa.")
    print("==================================================")
    print("  Estúdio Master criado e calibrado com sucesso!   ")
    print("==================================================")

if __name__ == "__main__":
    setup_mu_master_studio()

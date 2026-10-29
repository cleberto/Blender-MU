import bpy
import math

def setup_mu_master_studio():
    # 1. Configuração do Motor de Render (Cycles + AgX)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    if hasattr(bpy.context.preferences.addons.get('cycles'), 'preferences'):
        bpy.context.preferences.addons['cycles'].preferences.get_devices()
        scene.cycles.device = 'GPU'
    
    scene.cycles.samples = 256
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    
    # Gerenciamento de Cores Profissional
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'Medium High Contrast'
    scene.view_settings.exposure = 0.0
    
    # 2. Criar Coleção de Estúdio
    col_name = "90_STUDIO_LIGHTS"
    col = bpy.data.collections.get(col_name)
    if not col:
        col = bpy.data.collections.new(col_name)
        scene.collection.children.link(col)
    
    # Limpar luzes e câmeras antigas do estúdio
    for obj in list(col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
        
    # 3. Luz Principal (Key Light) - 45 graus, suave
    key_data = bpy.data.lights.new(name="Key_Light", type='AREA')
    key_data.energy = 350
    key_data.size = 2.0
    key_data.color = (1.0, 0.96, 0.92) # Luz ligeiramente quente
    key_obj = bpy.data.objects.new("Key_Light", key_data)
    key_obj.location = (-2.5, -2.5, 3.0)
    key_obj.rotation_euler = (math.radians(50), math.radians(10), math.radians(-45))
    col.objects.link(key_obj)
    
    # 4. Luz de Preenchimento (Fill Light) - Suave e fria
    fill_data = bpy.data.lights.new(name="Fill_Light", type='AREA')
    fill_data.energy = 120
    fill_data.size = 3.5
    fill_data.color = (0.85, 0.92, 1.0) # Contraste frio
    fill_obj = bpy.data.objects.new("Fill_Light", fill_data)
    fill_obj.location = (3.0, -2.0, 1.5)
    fill_obj.rotation_euler = (math.radians(65), math.radians(-10), math.radians(55))
    col.objects.link(fill_obj)
    
    # 5. Luz de Recorte (Rim/Back Light) - Destacar silhueta e escamas
    rim_data = bpy.data.lights.new(name="Rim_Light", type='SPOT')
    rim_data.energy = 600
    rim_data.spot_size = math.radians(60)
    rim_data.spot_blend = 0.3
    rim_data.color = (1.0, 1.0, 1.0)
    rim_obj = bpy.data.objects.new("Rim_Light", rim_data)
    rim_obj.location = (0.0, 3.5, 3.5)
    rim_obj.rotation_euler = (math.radians(-45), 0, math.radians(180))
    col.objects.link(rim_obj)
    
    # 6. Câmera Focal 85mm (Padrão Colecionável/Hero Shot)
    cam_data = bpy.data.cameras.new("Hero_Camera")
    cam_data.lens = 85
    cam_obj = bpy.data.objects.new("Hero_Camera", cam_data)
    cam_obj.location = (0.0, -4.5, 1.2)
    cam_obj.rotation_euler = (math.radians(82), 0, 0)
    col.objects.link(cam_obj)
    scene.camera = cam_obj
    
    print("[MU Studio] Estúdio mestre criado com sucesso!")

if __name__ == "__main__":
    setup_mu_master_studio()

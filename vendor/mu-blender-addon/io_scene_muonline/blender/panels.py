# -*- coding: utf-8 -*-
"""MU Online - 3D viewport side panel (BMD models / map import / map export)."""

import bpy
from bpy.types import Panel


class MUONLINE_PT_main(Panel):
    bl_label = "MU Online (Mu2Blender)"
    bl_idname = "MUONLINE_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MU Online"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        self._draw_bmd(layout, scene)

    # ---------------- BMD models ----------------
    def _draw_bmd(self, layout, scene):
        box = layout.box()
        box.label(text="BMD \u6a21\u578b", icon="ARMATURE_DATA")

        col = box.column(align=True)
        col.label(text="\u5bfc\u5165", icon="IMPORT")
        imp = scene.muonline_import
        sub = col.column(align=True)
        sub.prop(imp, "scale")
        sub.prop(imp, "load_textures")
        sub.prop(imp, "flip_normals")
        sub.prop(imp, "flip_uv")
        sub.prop(imp, "use_vertex_normals")
        sub.prop(imp, "auto_fit")
        row = col.row()
        row.scale_y = 1.4
        row.operator("import_scene.muonline_bmd", text="\u5bfc\u5165 BMD \u6a21\u578b")

        col = box.column(align=True)
        col.separator()
        col.label(text="\u5bfc\u51fa", icon="EXPORT")
        exp = scene.muonline_export
        sub = col.column(align=True)
        sub.prop(exp, "version")
        sub.prop(exp, "scale")
        sub.prop(exp, "export_textures")
        # \u56de\u8f6c\u5bfc\u51fa (BMD \u2192 Blender \u2192 BMD)
        row = col.row()
        row.scale_y = 1.4
        row.operator("export_scene.muonline_bmd", text="\u5bfc\u51fa BMD \u6a21\u578b (\u56de\u8f6c)")

        # \u901a\u7528\u7f51\u683c\u5bfc\u51fa (FBX/GLB):\u7528\u540c\u4e00\u4e2a\u901a\u7528\u5bfc\u51fa\u500d\u6570
        col.separator()
        col.label(text="\u901a\u7528\u7f51\u683c\u5bfc\u51fa (FBX/GLB)", icon="MESH_DATA")
        sub2 = col.column(align=True)
        sub2.prop(exp, "generic_scale")
        row = col.row()
        row.scale_y = 1.4
        row.operator("export_scene.muonline_bmd_animated",
                     text="\u5e26\u52a8\u753b\u5bfc\u51fa BMD")
        row = col.row()
        row.scale_y = 1.4
        row.operator("export_scene.muonline_bmd_generic",
                     text="\u5bfc\u51fa\u7eaf\u9759\u6001 BMD (\u65e0\u52a8\u753b)")


def register():
    pass


def unregister():
    pass

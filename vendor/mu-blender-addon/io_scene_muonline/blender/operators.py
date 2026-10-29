# -*- coding: utf-8 -*-
"""Import/export operators - file pickers + calls into importer/exporter."""

import os

import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper, ExportHelper

from ..formats.bmd import parse_bmd


def _import_props(context):
    return context.scene.muonline_import


def _export_props(context):
    return context.scene.muonline_export


def _read_file(path):
    with open(path, "rb") as f:
        return f.read()


# ---------------------------------------------------------------- 导入 BMD


class MUONLINE_OT_import_bmd(Operator, ImportHelper):
    bl_idname = "import_scene.muonline_bmd"
    bl_label = "Import MU BMD"
    bl_description = "\u5bfc\u5165 MU Online .bmd \u6a21\u578b(\u7f51\u683c/\u9aa8\u67b6/\u52a8\u4f5c)"
    bl_options = {"REGISTER", "UNDO"}

    filename_ext = ".bmd"
    filter_glob: bpy.props.StringProperty(default="*.bmd", options={"HIDDEN"})
    files: bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)

    def execute(self, context):
        props = _import_props(context)
        files = [self.filepath] if not self.files else [
            os.path.join(os.path.dirname(self.filepath), f.name) for f in self.files
        ]

        imported = 0
        for path in files:
            try:
                data = _read_file(path)
                bmd = parse_bmd(data)
                from ..importer.bmd_importer import import_bmd
                import_bmd(
                    bmd,
                    name=bmd.name or os.path.splitext(os.path.basename(path))[0],
                    scale=props.scale,
                    load_textures=props.load_textures,
                    texture_root=props.texture_root or None,
                    flip_normals=props.flip_normals,
                    flip_uv=props.flip_uv,
                    use_vertex_normals=props.use_vertex_normals,
                    bmd_dir=os.path.dirname(path),
                    auto_fit=props.auto_fit,
                )
                imported += 1
            except Exception as exc:
                self.report({"ERROR"}, "\u5bfc\u5165\u5931\u8d25 %s: %s" % (os.path.basename(path), exc))
                import traceback
                traceback.print_exc()

        self.report({"INFO"}, "\u5df2\u5bfc\u5165 %d/%d \u4e2a BMD" % (imported, len(files)))
        return {"FINISHED"}


# ---------------------------------------------------------------- 导出 BMD


class MUONLINE_OT_export_bmd(Operator, ExportHelper):
    bl_idname = "export_scene.muonline_bmd"
    bl_label = "Export MU BMD"
    bl_description = "\u5bfc\u51fa\u6240\u9009\u7f51\u683c\uff08+\u9aa8\u67b6\uff09\u4e3a MU Online .bmd \u6587\u4ef6"

    filename_ext = ".bmd"
    filter_glob: bpy.props.StringProperty(default="*.bmd", options={"HIDDEN"})

    def execute(self, context):
        props = _export_props(context)
        sel = context.selected_objects
        arm_obj = None
        # If an armature is selected, find the meshes that use it.
        arm_obj = next((o for o in sel if o.type == "ARMATURE"), None)
        if arm_obj is not None:
            mesh_objs = []
            for o in context.scene.objects:
                if o.type != "MESH":
                    continue
                if o.parent is arm_obj:
                    mesh_objs.append(o)
                    continue
                for mod in o.modifiers:
                    if mod.type == "ARMATURE" and mod.object is arm_obj:
                        mesh_objs.append(o)
                        break
        else:
            mesh_objs = [o for o in sel if o.type == "MESH"]
            for o in mesh_objs:
                for mod in o.modifiers:
                    if mod.type == "ARMATURE" and mod.object:
                        arm_obj = mod.object
                        break
                if arm_obj:
                    break

        if not mesh_objs:
            self.report({"ERROR"}, "\u8bf7\u5148\u9009\u62e9\u6a21\u578b\u7684\u9aa8\u67b6(\u6216\u5176\u7f51\u683c)")
            return {"CANCELLED"}

        try:
            from ..exporter.bmd_exporter import export_bmd, export_mesh_textures
            from ..formats.bmd import write_bmd
            # Round-trip scale: if the user left the export scale at the
            # default 1.0, reuse the scale the model was imported with.
            scale = props.scale
            src = arm_obj if arm_obj is not None else (mesh_objs[0] if mesh_objs else None)
            if scale == 1.0 and src is not None:
                scale = getattr(getattr(src, "muonline", None), "import_scale", 1.0) or 1.0
            bmd = export_bmd(
                arm_obj, mesh_objs,
                name=os.path.splitext(os.path.basename(self.filepath))[0],
                version=int(props.version),
                scale=scale,
            )
            with open(self.filepath, "wb") as f:
                f.write(write_bmd(bmd, version=int(props.version)))
            ntex = 0
            if getattr(props, "export_textures", True):
                tex_dir = os.path.dirname(self.filepath)
                ntex = export_mesh_textures(mesh_objs, tex_dir)
        except Exception as exc:
            self.report({"ERROR"}, "\u5bfc\u51fa\u5931\u8d25: %s" % exc)
            import traceback
            traceback.print_exc()
            return {"CANCELLED"}

        self.report({"INFO"}, "\u5df2\u5bfc\u51fa %d \u4e2a BMD \u7f51\u683c + %d \u4e2a\u7eb9\u7406\u5230 %s" % (
            len(bmd.meshes), len(ntex) if isinstance(ntex, (list, tuple)) else ntex,
            self.filepath))
        return {"FINISHED"}


# ---------------------------------------------------------------- 导出地图


# ---------------------------------------------------------------- ???


class MUONLINE_OT_export_bmd_generic(Operator, ExportHelper):
    bl_idname = "export_scene.muonline_bmd_generic"
    bl_label = "Export MU BMD (Static)"
    bl_description = ("\u5bfc\u51fa\u6240\u9009\u7f51\u683c\uff08FBX/OBJ/GLB...\uff09\u4e3a\u65e0\u52a8\u753b\u7684 MU .bmd"
                      "\u5e76\u540c\u65f6\u5bfc\u51fa\u5176\u6750\u8d28\u7eb9\u7406")

    filename_ext = ".bmd"
    filter_glob: bpy.props.StringProperty(default="*.bmd", options={"HIDDEN"})

    #: selection captured before the file dialog steals focus
    _sel_names = None

    def invoke(self, context, event):
        # ExportHelper opens a file browser; grab the 3D-view selection first
        # so it is still available when execute() finally runs.
        self._sel_names = [o.name for o in context.selected_objects]
        return super().invoke(context, event)

    def _collect_mesh_objects(self, context):
        """Selected meshes + mesh descendants of selected roots (FBX/OBJ
        rigs are usually selected as the armature/empty root, not the mesh)."""
        if getattr(self, "_sel_names", None):
            roots = [bpy.data.objects.get(n) for n in self._sel_names]
            roots = [o for o in roots if o is not None]
        else:
            roots = list(context.selected_objects)
        out = []
        seen = set()

        def walk(o):
            if o is None or o.name in seen:
                return
            seen.add(o.name)
            if o.type == "MESH":
                out.append(o)
            for c in o.children:
                walk(c)

        for o in roots:
            walk(o)
        return out

    def execute(self, context):
        props = _export_props(context)
        mesh_objs = self._collect_mesh_objects(context)
        if not mesh_objs:
            self.report({"ERROR"}, "\u8bf7\u5148\u9009\u62e9\u4e00\u4e2a\u6216\u591a\u4e2a\u7f51\u683c\u5bf9\u8c61")
            return {"CANCELLED"}
        # optional armature found via an Armature modifier
        arm_obj = None
        for o in mesh_objs:
            for mod in o.modifiers:
                if mod.type == "ARMATURE" and mod.object:
                    arm_obj = mod.object
                    break
            if arm_obj:
                break
        try:
            from ..exporter.generic_bmd_exporter import export_generic_bmd
            from ..exporter.bmd_exporter import export_mesh_textures
            from ..formats.bmd import write_bmd
            # generic_scale is an intuitive multiplier: exported BMD
            # coords = Blender coords x generic_scale.
            bmd = export_generic_bmd(
                arm_obj, mesh_objs,
                name=os.path.splitext(os.path.basename(self.filepath))[0],
                version=int(props.version),
                scale_multiplier=props.generic_scale,
                # static export: only the bind action (action 0), no clip actions
                export_actions=False,
            )
            with open(self.filepath, "wb") as f:
                f.write(write_bmd(bmd, version=int(props.version)))
            ntex = export_mesh_textures(mesh_objs, os.path.dirname(self.filepath))
        except Exception as exc:
            self.report({"ERROR"}, "\u901a\u7528\u5bfc\u51fa\u5931\u8d25: %s" % exc)
            import traceback
            traceback.print_exc()
            return {"CANCELLED"}
        self.report({"INFO"}, "\u5df2\u5bfc\u51fa %d \u4e2a BMD \u7f51\u683c + %d \u4e2a\u7eb9\u7406" % (
            len(bmd.meshes),
            len(ntex) if isinstance(ntex, (list, tuple)) else ntex))
        return {"FINISHED"}


# ---------------------------------------------------------------- \u5e26\u52a8\u753b\u5bfc\u51fa


class MUONLINE_OT_export_bmd_animated(Operator, ExportHelper):
    """\u5bf9\u9009\u4e2d\u7684 FBX/GLB \u9aa8\u67b6 + \u7f51\u683c\u8fde\u52a8\u753b\u4e00\u8d77\u5bfc\u51fa\u4e3a MU BMD\u3002
    \u4e0e\u9759\u6001\u5bfc\u51fa(\u901a\u7528\u7f51\u683c)\u7684\u533a\u522b\uff1a\u4fdd\u7559\u9aa8\u9abc\uff0c\u5e76\u5c06\u9aa8\u9abc\u52a8\u753b\u5199\u5165 BMD \u7684 action\uff08\u5305\u542b bind \u52a8\u4f5c\u548c\u5176\u4f59\u526f\u672c\u52a8\u4f5c\uff09\u3002"""
    bl_idname = "export_scene.muonline_bmd_animated"
    bl_label = "Export MU BMD (Animated)"
    bl_description = ("\u5bfc\u51fa\u6240\u9009 FBX/GLB \u9aa8\u67b6 + \u5176\u7f51\u683c\u4e3a MU .bmd\uff0c"
                      "\u5d4c\u5165\u9aa8\u9abc\u52a8\u753b\uff08bind + \u52a8\u4f5c\uff09")

    filename_ext = ".bmd"
    filter_glob: bpy.props.StringProperty(default="*.bmd", options={"HIDDEN"})

    #: selection captured before the file dialog steals focus
    _sel_names = None

    def invoke(self, context, event):
        # ExportHelper opens a file browser; grab the 3D-view selection first
        # so it is still available when execute() finally runs.
        self._sel_names = [o.name for o in context.selected_objects]
        return super().invoke(context, event)

    def _collect(self, context):
        """\u6536\u96c6 (armature, mesh\u5217\u8868)\uff1a\u9009\u4e2d\u7684\u9aa8\u67b6 + \u6240\u6709\u7ed1\u5b9a\u7684\u7f51\u683c\u3002
        FBX/GLB \u5bfc\u5165\u65f6\u901a\u5e38\u9009\u4e2d\u9aa8\u67b6\u6839\u8282\u70b9\u800c\u975e\u7f51\u683c\uff0c\u56e0\u6b64\u4ece\u6839\u5411\u4e0b\u904d\u5386,\u540c\u65f6\u6536\u96c6 Armature \u548c\u6240\u6709\u7f51\u683c\u540e\u4ee3\u3002"""
        if getattr(self, "_sel_names", None):
            roots = [bpy.data.objects.get(n) for n in self._sel_names]
            roots = [o for o in roots if o is not None]
        else:
            roots = list(context.selected_objects)
        meshes = []
        arm_obj = None
        seen = set()

        def walk(o):
            nonlocal arm_obj
            if o is None or o.name in seen:
                return
            seen.add(o.name)
            if o.type == "MESH":
                meshes.append(o)
            elif o.type == "ARMATURE" and arm_obj is None:
                arm_obj = o
            for c in o.children:
                walk(c)

        for o in roots:
            walk(o)
        # \u82e5\u672a\u9009\u4e2d\u9aa8\u67b6,\u5219\u901a\u8fc7\u7f51\u683c\u7684 Armature \u4fee\u6539\u5668\u627e\u5230\u5b83
        if arm_obj is None:
            for o in meshes:
                for mod in o.modifiers:
                    if mod.type == "ARMATURE" and mod.object:
                        arm_obj = mod.object
                        break
                if arm_obj:
                    break
        return arm_obj, meshes

    def execute(self, context):
        props = _export_props(context)
        arm_obj, mesh_objs = self._collect(context)
        if not mesh_objs:
            self.report({"ERROR"}, "\u8bf7\u5148\u9009\u62e9\u4e00\u4e2a\u6216\u591a\u4e2a\u7f51\u683c\u5bf9\u8c61\u6216\u5176\u9aa8\u67b6")
            return {"CANCELLED"}
        try:
            from ..exporter.generic_bmd_exporter import export_generic_bmd
            from ..exporter.bmd_exporter import export_mesh_textures
            from ..formats.bmd import write_bmd
            # generic_scale \u662f\u7b80\u660e\u7684\u4e58\u6570:\u5bfc\u51fa BMD \u5750\u6807 = Blender \u5750\u6807 x generic_scale
            bmd = export_generic_bmd(
                arm_obj, mesh_objs,
                name=os.path.splitext(os.path.basename(self.filepath))[0],
                version=int(props.version),
                scale_multiplier=props.generic_scale,
                export_actions=True,
            )
            with open(self.filepath, "wb") as f:
                f.write(write_bmd(bmd, version=int(props.version)))
            ntex = export_mesh_textures(mesh_objs, os.path.dirname(self.filepath))
        except Exception as exc:
            self.report({"ERROR"}, "\u5e26\u52a8\u753b\u5bfc\u51fa\u5931\u8d25: %s" % exc)
            import traceback
            traceback.print_exc()
            return {"CANCELLED"}
        self.report({"INFO"}, "\u5df2\u5bfc\u51fa %d \u4e2a BMD \u7f51\u683c + %d \u4e2a\u7eb9\u7406 (\u542b\u52a8\u753b)" % (
            len(bmd.meshes),
            len(ntex) if isinstance(ntex, (list, tuple)) else ntex))
        return {"FINISHED"}


# ---------------------------------------------------------------- \u6587\u4ef6\u83dc\u5355


def menu_func_import(self, context):
    self.layout.operator(MUONLINE_OT_import_bmd.bl_idname, text="MU Online (.bmd)")


def menu_func_export(self, context):
    self.layout.operator(MUONLINE_OT_export_bmd.bl_idname, text="MU BMD \u56de\u8f6c\u5bfc\u51fa (.bmd)")
    self.layout.operator(MUONLINE_OT_export_bmd_animated.bl_idname,
                         text="MU BMD \u5e26\u52a8\u753b\u5bfc\u51fa (.bmd)")
    self.layout.operator(MUONLINE_OT_export_bmd_generic.bl_idname,
                         text="MU BMD \u7eaf\u9759\u6001\u5bfc\u51fa (.bmd)")


def register():
    from bpy.types import TOPBAR_MT_file_import, TOPBAR_MT_file_export
    TOPBAR_MT_file_import.append(menu_func_import)
    TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    from bpy.types import TOPBAR_MT_file_import, TOPBAR_MT_file_export
    TOPBAR_MT_file_import.remove(menu_func_import)
    TOPBAR_MT_file_export.remove(menu_func_export)

# -*- coding: utf-8 -*-
"""Import/export properties and per-object custom attributes."""

import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import PropertyGroup


class MUOnlineImportProperties(PropertyGroup):
    scale: FloatProperty(
        name="Scale",
        description="Global scale (BMD units -> Blender units)",
        default=1.0, min=0.0001, soft_max=100.0,
    )
    load_textures: BoolProperty(
        name="Load Textures",
        description="Load OZJ/OZT/TGA textures from the texture folder",
        default=True,
    )
    flip_normals: BoolProperty(
        name="Flip Normals",
        description="Flip face normals (for some mirrored models)",
        default=False,
    )
    flip_uv: BoolProperty(
        name="Flip UV (V)",
        description="Flip V axis (game uses v=0 = top)",
        default=True,
    )
    use_vertex_normals: BoolProperty(
        name="Use BMD Normals",
        description="Apply BMD stored normals for smooth shading "
                      "(disable if a mesh shades abnormally)",
        default=False,
    )
    auto_fit: BoolProperty(
        name="Auto-fit to 2m",
        description="Scale the model so its largest dimension is ~2 Blender units",
        default=True,
    )
    texture_root: StringProperty(
        name="Texture Root",
        description="MU client texture root folder (World/Texture etc.)",
        subtype="DIR_PATH", default="",
    )
    object_bmd_root: StringProperty(
        name="Object BMD Root",
        description="Object folder root (for instancing Object#.bmd)",
        subtype="DIR_PATH", default="",
    )


class MUOnlineExportProperties(PropertyGroup):
    version: EnumProperty(
        name="BMD \u7248\u672c",
        description="\u5bfc\u51fa\u7684 BMD \u7248\u672c",
        items=[
            ("12", "v12 (FileCryptor)", "Official server common, encrypted"),
            ("10", "v10 (Plain)", "Plain text (0x0A), for debugging"),
        ],
        default="12",
    )
    scale: FloatProperty(
        name="\u7f29\u653e",
        description="\u5bfc\u51fa\u7f29\u653e (Blender \u5355\u4f4d -> BMD \u5355\u4f4d)",
        default=1.0, min=0.0001, soft_max=100.0,
    )
    generic_scale: FloatProperty(
        name="\u901a\u7528\u5bfc\u51fa\u500d\u6570",
        description=("\u5bfc\u51fa\u5750\u6807 = Blender \u5750\u6807 x \u6b64\u500d\u6570"
                     " (>1 \u653e\u5927, <1 \u7f29\u5c0f)"),
        default=1.0, min=0.0001, soft_max=1000.0,
    )
    export_bind_action: BoolProperty(
        name="\u5bfc\u51fa\u7ed1\u5b9a\u4e3a\u52a8\u4f5c 0",
        description="\u5c06\u9aa8\u9abc\u9759\u6b62\u59ff\u52bf\u5199\u4e3a BMD action 0",
        default=True,
    )
    export_textures: BoolProperty(
        name="\u5bfc\u51fa\u7eb9\u7406",
        description="\u5c06\u6a21\u578b\u7eb9\u7406\u4ee5\u52a0\u5bc6\u7684 .ozj/.ozt \u5199\u5230 .bmd \u65c1\u8fb9",
        default=True,
    )


class MUOnlineObjectProperties(PropertyGroup):
    """Object custom props: mark import source metadata for BMD models."""

    is_mu_model: BoolProperty(default=False)
    texture_path: StringProperty(default="")
    import_scale: FloatProperty(default=1.0)

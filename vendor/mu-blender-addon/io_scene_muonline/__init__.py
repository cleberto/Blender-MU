# -*- coding: utf-8 -*-
"""io_scene_muonline - MU Online (Mu2Blender) BMD model & map import/export addon.

Module layout mirrors the TypeScript muonline-bmd-viewer project:
    formats/  pure data format readers/writers (no bpy dependency)
    crypto/   encryption algorithms
    utils/    shared helpers
    importer/ data -> Blender scene
    exporter/ Blender scene -> data
    blender/  bpy-dependent layer (operators / panels / properties)
"""

bl_info = {
    "name": "MU Online (Mu2Blender) - BMD Model & Map Import/Export",
    "author": "Mu2Blender",
    "version": (0, 1, 0),
    "blender": (3, 6, 0),
    "location": "File > Import/Export > MU Online (...)",
    "description": (
        "Import/Export MU Online BMD models (with armature & actions), "
        "terrain (ATT/MAP/OZB) and map objects (EncTerrain.obj)."
    ),
    "category": "Import-Export",
}

if "bpy" in locals():
    import importlib
    from . import blender, importer, exporter, formats, crypto, utils  # noqa

    for _m in (utils, crypto, formats, importer, exporter, blender):
        importlib.reload(_m)

# Allow importing formats/crypto in a plain Python environment for unit tests
try:
    import bpy  # noqa
    _HAS_BPY = True
except ImportError:
    bpy = None
    _HAS_BPY = False


def _register_internal():
    from bpy.types import Object, Scene

    from . import blender as _blender
    from .blender.properties import (
        MUOnlineImportProperties,
        MUOnlineExportProperties,
        MUOnlineObjectProperties,
    )
    from .blender.operators import (
        MUONLINE_OT_import_bmd,
        MUONLINE_OT_export_bmd,
        MUONLINE_OT_export_bmd_generic,
        MUONLINE_OT_export_bmd_animated,
    )
    from .blender.panels import MUONLINE_PT_main

    _classes = (
        MUOnlineImportProperties,
        MUOnlineExportProperties,
        MUOnlineObjectProperties,
        MUONLINE_OT_import_bmd,
        MUONLINE_OT_export_bmd,
        MUONLINE_OT_export_bmd_generic,
        MUONLINE_OT_export_bmd_animated,
        MUONLINE_PT_main,
    )

    for cls in _classes:
        bpy.utils.register_class(cls)

    Scene.muonline_import = bpy.props.PointerProperty(type=MUOnlineImportProperties)
    Scene.muonline_export = bpy.props.PointerProperty(type=MUOnlineExportProperties)
    Object.muonline = bpy.props.PointerProperty(type=MUOnlineObjectProperties)

    _blender.operators.register()
    _blender.panels.register()
    return _classes


def _unregister_internal(_classes):
    from bpy.types import Object, Scene
    from . import blender as _blender

    _blender.operators.unregister()
    _blender.panels.unregister()

    del Object.muonline
    del Scene.muonline_import
    del Scene.muonline_export

    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)


_CLASSES = ()


def register():
    global _CLASSES
    _CLASSES = _register_internal()


def unregister():
    if _HAS_BPY:
        _unregister_internal(_CLASSES)


if __name__ == "__main__":
    register()

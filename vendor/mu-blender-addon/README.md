# MU BMD addon snapshot

`io_scene_muonline/` starts as a source-only snapshot of `D:\source\mu-blender-addon-main\io_scene_muonline` taken on 2026-10-18. `upstream-20261018.zip` preserves that exact snapshot (SHA-256 `E13AD5FAFFD30556ED4D04824C515F47C68BE708854F0FF0DCD34B404465952B`). `manifest.json` records the SHA-256 of each active Python file. The supplied addon reports version 0.1.0. Its separate map editor and standalone exporter were not copied because the current Dragon audit uses only this BMD package.

The zip is the immutable baseline for local modernization. Change the active `io_scene_muonline/` in small, tested revisions and refresh `manifest.json` with the new active hashes. Describe each change in a run record; the zip lets another agent compare against the untouched baseline. No license file was present in the supplied directory; check provenance and redistribution terms before publishing a derivative package.

Current result on Blender 5.2.2: BMD geometry, armature and seven actions import with textures off. Textures on fail because the embedded Python cannot import Pillow; the addon leaves `Image` undefined in `formats/textures.py`. The importer also reports 29/39 rest/bind mismatches for Monster03. See `catalog/runs/monster03-v0001-audit-20261018.json`.

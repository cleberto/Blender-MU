"""Extract a small contact sheet from the supplied comparison movie in Blender."""

import bpy
import sys
from pathlib import Path

ROOT = Path(r"D:\source\Blender")
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SOURCE = Path(args[0]) if args else ROOT / "models" / "budge-dragon-old-vs-new.mp4"
OUT = Path(args[1]) if len(args) > 1 else ROOT / "work" / "monster03" / "turntable" / "reference-frames"
OUT.mkdir(parents=True, exist_ok=True)

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.use_sequencer = True
editor = scene.sequence_editor_create()
strip = editor.strips.new_movie("reference", str(SOURCE), channel=1, frame_start=1)
duration = strip.frame_duration
print(f"REFERENCE duration_frames={duration} fps={scene.render.fps} source={SOURCE}")
for fraction in (0, 0.1, 0.25, 0.5, 0.75, 0.9):
    frame = 1 + round((duration - 1) * fraction)
    scene.frame_set(frame)
    scene.render.filepath = str(OUT / f"reference-{fraction:.2f}.png")
    bpy.ops.render.render(write_still=True)
    print(f"EXTRACTED {frame} {scene.render.filepath}")

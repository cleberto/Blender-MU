"""Create a labeled paired contact sheet from two deterministic turntables."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


if len(sys.argv) != 4:
    raise SystemExit("usage: compose_turntable_comparison.py <left_dir> <right_dir> <output.png>")
left_dir, right_dir, output = map(Path, sys.argv[1:])
left = sorted(left_dir.glob("frame-*.png"))
right = sorted(right_dir.glob("frame-*.png"))
if not left or len(left) != len(right):
    raise RuntimeError("turntables must contain the same non-zero number of frames")

tile, header, columns = 300, 36, 4
rows = (len(left) + columns - 1) // columns
sheet = Image.new("RGB", (columns * tile * 2, rows * (tile + header)), "#17191d")
font = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 18)
small = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 14)
draw = ImageDraw.Draw(sheet)
for index, (left_path, right_path) in enumerate(zip(left, right)):
    col, row = index % columns, index // columns
    x, y = col * tile * 2, row * (tile + header)
    draw.text((x + 8, y + 8), f"{index * 45:03d}° | HD inherited", font=small, fill="#d7d7d7")
    draw.text((x + tile + 8, y + 8), "PBR calibration", font=small, fill="#b9d9ff")
    for offset, path in ((0, left_path), (tile, right_path)):
        with Image.open(path) as image:
            image = image.convert("RGB").resize((tile, tile), Image.Resampling.LANCZOS)
        sheet.paste(image, (x + offset, y + header))
output.parent.mkdir(parents=True, exist_ok=True)
sheet.save(output, optimize=True)
print(output)

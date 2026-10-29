"""Compose Blender full-body action frames into a labeled 7x3 contact sheet."""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

folder = Path(sys.argv[1])
rows = json.loads((folder / "frames.json").read_text(encoding="utf-8"))
actions = list(dict.fromkeys(row["action"] for row in rows))
width, height = 3 * 420, len(actions) * 420
sheet = Image.new("RGB", (width, height), "#17191d")
font = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 23)
for row_index, action in enumerate(actions):
    for row in (entry for entry in rows if entry["action"] == action):
        with Image.open(folder / row["image"]) as image:
            image = image.convert("RGB").resize((400, 400), Image.Resampling.LANCZOS)
        x, y = row["slot"] * 420 + 10, row_index * 420 + 10
        sheet.paste(image, (x, y))
        draw = ImageDraw.Draw(sheet)
        draw.rectangle((x + 4, y + 4, x + 200, y + 37), fill="#15171b")
        draw.text((x + 10, y + 7), f"{action}  quadro {row['frame']}", font=font, fill="white")
path = folder / "full-body-actions.png"
sheet.save(path, optimize=True)
print(f"POSE_SHEET={path}")

"""Prepare honest side-by-side frames for the Monster03 diagnostic MP4.

The left candidate is the v0002 isolated mechanical head; the right source is
the received full HD GLB. Both are shown in an identical head camera protocol.
Encoding is performed by Blender's VSE in encode_monster03_comparison_video.py.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "work" / "monster03"
SOURCE = BASE / "video-renders"
OUT = BASE / "comparison-video"
OUT.mkdir(parents=True, exist_ok=True)

FONT_REGULAR = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")


def font(size, bold=False):
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size)


def center(draw, y, text, size, color, bold=False):
    face = font(size, bold)
    box = draw.textbbox((0, 0), text, font=face)
    draw.text(((1280 - (box[2] - box[0])) / 2, y), text, font=face, fill=color)


def panel(draw, x, label, caption, label_color):
    draw.rounded_rectangle((x, 95, x + 580, 658), radius=14, fill="#25282d")
    draw.rectangle((x, 95, x + 580, 102), fill=label_color)
    draw.text((x + 16, 117), label, font=font(30, True), fill="#ffffff")
    draw.text((x + 16, 155), caption, font=font(19), fill="#c7cbd0")


def make_main(index):
    canvas = Image.new("RGB", (1280, 720), "#15171b")
    draw = ImageDraw.Draw(canvas)
    draw.text((39, 21), "BUDGE DRAGON  |  MEU x DELE", font=font(34, True), fill="#f5f5f5")
    draw.text((1043, 31), "360°  /  01", font=font(20, True), fill="#a9b0ba")
    panel(draw, 36, "MEU  •  v0002", "Estudo funcional da cabeça", "#ca684f")
    panel(draw, 664, "DELE  •  HD recebido", "Dragão completo, recorte da cabeça", "#6aa0c5")
    for x, variant in ((46, "ours"), (674, "legacy")):
        path = SOURCE / variant / "head" / f"frame-{index:02d}.png"
        with Image.open(path) as source:
            image = ImageOps.contain(source.convert("RGB"), (560, 450))
        canvas.paste(image, (x + (560 - image.width) // 2, 195 + (450 - image.height) // 2))
    draw.text((37, 677), "Mesmo ângulo, câmera e iluminação  •  quadro parado da animação 00", font=font(19), fill="#c9ccd1")
    canvas.save(OUT / f"compare-{index:02d}.png", optimize=True)


def make_card(name, title, lines):
    canvas = Image.new("RGB", (1280, 720), "#15171b")
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((42, 45, 1238, 675), radius=20, fill="#22262c")
    draw.rectangle((42, 45, 1238, 54), fill="#ca684f")
    center(draw, 115, title, 47, "#ffffff", True)
    y = 257
    for line in lines:
        center(draw, y, line, 27, "#d0d3d9")
        y += 58
    canvas.save(OUT / f"{name}.png", optimize=True)


for index in range(48):
    make_main(index)

make_card("intro", "BUDGE DRAGON  |  MEU x DELE", [
    "Comparação de cabeça em rotação de 360°",
    "Mesma câmera e iluminação para os dois modelos",
])
make_card("outro", "LEITURA HONESTA DO ESTADO ATUAL", [
    "Meu: teste de articulação da boca; ainda sem corpo e textura.",
    "Dele: visual HD completo; boca fechada no modelo recebido.",
    "Próxima etapa: integrar a mandíbula à escultura fiel ao HD.",
])
preview_paths = ([OUT / "intro.png"]
                 + [OUT / f"compare-{index:02d}.png" for _ in range(2) for index in range(48)]
                 + [OUT / "outro.png"])
preview_frames = []
for path in preview_paths:
    with Image.open(path) as source:
        preview_frames.append(source.convert("RGB").resize((640, 360), Image.Resampling.LANCZOS))
preview_frames[0].save(
    OUT / "budge-dragon-meu-vs-dele-preview.webp",
    save_all=True,
    append_images=preview_frames[1:],
    duration=[1000] + [83] * 96 + [3000],
    loop=0,
    quality=82,
    method=4,
)
print(f"COMPARISON_FRAMES={OUT}")

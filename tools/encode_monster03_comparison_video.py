"""Write the comparison as a portable MJPEG AVI without external encoders.

The installed Blender build decodes movies but exposes no FFMPEG output format.
This deterministic RIFF/AVI writer keeps the video reproducible on that host.
"""

import io
import struct
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "monster03" / "comparison-video"
VIDEO = OUT / "budge-dragon-meu-vs-dele.avi"
WIDTH, HEIGHT, FPS = 1280, 720, 24


def chunk(tag, payload):
    return tag + struct.pack("<I", len(payload)) + payload + (b"\0" if len(payload) & 1 else b"")


def listing(tag, payload):
    return chunk(b"LIST", tag + payload)


def jpeg(path):
    with Image.open(path) as image:
        image = image.convert("RGB")
        assert image.size == (WIDTH, HEIGHT), (path, image.size)
        stream = io.BytesIO()
        image.save(stream, "JPEG", quality=91, subsampling=0, optimize=True)
        return stream.getvalue()


intro = jpeg(OUT / "intro.png")
outro = jpeg(OUT / "outro.png")
comparison = [jpeg(OUT / f"compare-{index:02d}.png") for index in range(48)]
frames = [intro] * 24
for loop in range(2):
    for frame in comparison:
        frames.extend((frame, frame))
frames.extend([outro] * 72)
assert len(frames) == 288
max_size = max(map(len, frames))

avih = struct.pack(
    "<IIIIIIIIII4I", round(1_000_000 / FPS), max_size * FPS,
    0, 0x10, len(frames), 0, 1, max_size, WIDTH, HEIGHT, 0, 0, 0, 0,
)
strh = struct.pack(
    "<4s4sIHHIIIIIIIIhhhh", b"vids", b"MJPG", 0, 0, 0, 0,
    1, FPS, 0, len(frames), max_size, 0xFFFFFFFF, 0,
    0, 0, WIDTH, HEIGHT,
)
strf = struct.pack(
    "<IiiHHIIiiII", 40, WIDTH, HEIGHT, 1, 24,
    int.from_bytes(b"MJPG", "little"), WIDTH * HEIGHT * 3, 0, 0, 0, 0,
)
hdrl = listing(b"hdrl", chunk(b"avih", avih) + listing(b"strl", chunk(b"strh", strh) + chunk(b"strf", strf)))

movie = bytearray(b"movi")
index = bytearray()
for frame in frames:
    # AVI index offsets count from the four-byte 'movi' list type.
    index.extend(struct.pack("<4sIII", b"00dc", 0x10, len(movie), len(frame)))
    movie.extend(chunk(b"00dc", frame))

payload = b"AVI " + hdrl + chunk(b"LIST", bytes(movie)) + chunk(b"idx1", bytes(index))
VIDEO.write_bytes(b"RIFF" + struct.pack("<I", len(payload)) + payload)
print(f"COMPARISON_VIDEO={VIDEO} frames={len(frames)} fps={FPS} duration_s={len(frames)/FPS} bytes={VIDEO.stat().st_size}")

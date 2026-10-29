"""Decode the Monster03 OZJ/OZT source textures with Python's standard library.

Outputs are derived reference files; never modifies the original assets.
Usage: py -3.9 tools/decode_legacy_textures.py [output-directory]
"""

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "assets" / "original" / "monster03"


def chunk(kind, payload):
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def rgba_png(width, height, rows):
    header = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    data = b"".join(b"\x00" + row for row in rows)
    return header + chunk(b"IDAT", zlib.compress(data, 9)) + chunk(b"IEND", b"")


def decode_ozt(raw):
    if len(raw) < 22:
        raise ValueError("OZT header truncated")
    width, height, depth, _ = struct.unpack_from("<hhBB", raw, 16)
    if not (0 < width <= 4096 and 0 < height <= 4096 and depth == 32):
        raise ValueError("unsupported OZT dimensions/depth")
    if len(raw) < 22 + width * height * 4:
        raise ValueError("OZT pixel data truncated")
    rows = []
    for y in range(height):
        source_y = height - 1 - y  # OZT stores bottom row first.
        src = raw[22 + source_y * width * 4:22 + (source_y + 1) * width * 4]
        row = bytearray(len(src))
        for x in range(0, len(src), 4):
            b, g, r, a = src[x:x + 4]
            row[x:x + 4] = bytes((r, g, b, a))
        rows.append(bytes(row))
    return rgba_png(width, height, rows), [width, height]


def decode_ozj(raw):
    # This original starts with a 24-byte JPEG-like header followed by the image.
    marker = raw.find(b"\xff\xd8\xff", 24)
    if marker < 0:
        marker = raw.find(b"\xff\xd8\xff")
    if marker < 0:
        raise ValueError("OZJ JPEG marker missing")
    return raw[marker:], marker


def sha256(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", nargs="?", default=str(ROOT / "work" / "monster03" / "textures"))
    out = Path(parser.parse_args().output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    body = (SOURCES / "p_d.OZJ").read_bytes()
    wing = (SOURCES / "p_d.OZT").read_bytes()
    jpg, marker = decode_ozj(body)
    png, dimensions = decode_ozt(wing)
    (out / "p_d.jpg").write_bytes(jpg)
    (out / "p_d.png").write_bytes(png)
    report = {
        "source_sha256": {"p_d.OZJ": sha256(body), "p_d.OZT": sha256(wing)},
        "derived_sha256": {"p_d.jpg": sha256(jpg), "p_d.png": sha256(png)},
        "ozj_jpeg_offset": marker,
        "ozt_dimensions": dimensions,
        "output_dir": str(out),
    }
    (out / "decode-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

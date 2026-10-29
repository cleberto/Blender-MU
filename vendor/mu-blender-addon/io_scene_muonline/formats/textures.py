# -*- coding: utf-8 -*-
"""贴图 OZJ / OZT / TGA 编解码 —— 对应 TS 工程 src/ozj-loader.ts 与 C# OZTReader/OZJReader。

OZT: [0..15] 16B 头 | nx(s16)@16 | ny(s16)@18 | depth(u8)@20 | u1(u8)@21
     @22 起 BGRA 逐行(自底向上)。C# 版会把宽高补齐到 2 的幂(本模块默认保持真实尺寸,
     便于 Blender 使用;若需要可传 power_of_two=True)。
OZJ: [0..23] 24B 头(isTopDownSort@17) | @24 起内嵌 JPEG(允许向前扫描 FFD8FF)。
     若 !isTopDownSort 需垂直翻转。
TGA: 标准 TGA,交由 Pillow 处理。

依赖 Pillow(Blender 自带)。
"""

from io import BytesIO

try:
    from PIL import Image
    _HAS_PIL = True
except Exception:  # pragma: no cover
    _HAS_PIL = False


def _find_jpeg_start(data, from_=16):
    """扫描 JPEG 起始标记 FFD8FF。"""
    n = len(data)
    for i in range(from_, max(from_, n - 2)):
        if data[i] == 0xFF and data[i + 1] == 0xD8 and data[i + 2] == 0xFF:
            return i
    return -1


def decode_ozj(buf: bytes) -> Image.Image:
    # Some OZJ files in the wild are stored as a plain JPEG (or a 24-byte
    # header that is just a copy of the first 24 bytes of the JPEG). In that
    # case byte 17 is NOT a reliable isTopDownSort flag and the JPEG is a
    # standard top-down image, so we must NOT flip it. Detect by checking
    # whether the file starts with the JPEG SOI marker (FF D8 FF).
    if len(buf) >= 3 and buf[0:3] == b"\xff\xd8\xff":
        jpg_start = _find_jpeg_start(buf, 24)
        if jpg_start == -1:
            jpg_start = 24
        img = Image.open(BytesIO(buf[jpg_start:]))
        img.load()
        return img

    # Real OZJ header path: 24-byte header, isTopDownSort @17, JPEG from 24.
    jpg_start = _find_jpeg_start(buf, 16)
    if jpg_start == -1:
        raise ValueError("OZJ: JPEG marker not found")
    is_top_down = buf[17] != 0 if len(buf) > 17 else True

    img = Image.open(BytesIO(buf[jpg_start:]))
    img.load()
    if not is_top_down:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    return img


def decode_ozt(buf: bytes, power_of_two: bool = False) -> Image.Image:
    if len(buf) < 22:
        raise ValueError("OZT: file too small")
    nx = int.from_bytes(buf[16:18], "little", signed=True)
    ny = int.from_bytes(buf[18:20], "little", signed=True)
    depth = buf[20]

    expected = 22 + nx * ny * 4
    if not (0 < nx <= 1024 and 0 < ny <= 1024 and depth == 32 and expected <= len(buf)):
        raise ValueError("OZT: unsupported header")

    width = nx
    height = ny
    if power_of_two:
        width = _nearest_pow2(nx)
        height = _nearest_pow2(ny)

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = img.load()
    off = 22
    for y in range(ny):
        row = ny - 1 - y  # 自底向上
        for x in range(nx):
            b = buf[off]
            g = buf[off + 1]
            r = buf[off + 2]
            a = buf[off + 3]
            off += 4
            pixels[x, row] = (r, g, b, a)
    return img


def _nearest_pow2(v):
    p = 1
    while p < v:
        p <<= 1
    return p


def decode_tga(buf: bytes) -> Image.Image:
    img = Image.open(BytesIO(buf))
    img.load()
    return img


def decode_texture(buf: bytes, ext: str) -> Image.Image:
    """按扩展名自动解码贴图。ext 如 '.ozj'/'.ozt'/'.tga'/'.jpg'。"""
    ext = ext.lower()
    if ext == ".ozj":
        return decode_ozj(buf)
    if ext == ".ozt":
        return decode_ozt(buf)
    if ext in (".tga", ".jpg", ".jpeg", ".png"):
        return decode_tga(buf)
    raise ValueError(f"unsupported texture extension {ext}")


def encode_ozj(img: Image.Image, top_down: bool = True) -> bytes:
    """把 RGBA 图像编码为 OZJ。会先合成到 RGB(丢弃 alpha),再按标志决定是否翻转。"""
    if img.mode != "RGB":
        img = img.convert("RGB")
    if not top_down:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)

    jpg = BytesIO()
    img.save(jpg, format="JPEG", quality=95)

    header = bytearray(24)
    header[0:4] = (0x0A000002).to_bytes(4, "little")   # magic(与 C# 读取一致)
    header[4:6] = (1).to_bytes(2, "little")            # version
    header[6:10] = b"OZJ\x00"                          # format
    header[17] = 1 if top_down else 0
    return bytes(header) + jpg.getvalue()


def encode_ozt(img: Image.Image) -> bytes:
    """把 RGBA 图像编码为 OZT(自底向上 BGRA)。"""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    w, h = img.size
    header = bytearray(22)
    header[0:16] = b"\x00" * 16
    header[16:18] = w.to_bytes(2, "little", signed=True)
    header[18:20] = h.to_bytes(2, "little", signed=True)
    header[20] = 32
    header[21] = 0

    rows = []
    for y in range(h - 1, -1, -1):  # 自底向上
        for x in range(w):
            r, g, b, a = img.getpixel((x, y))
            rows.append(bytes((b, g, r, a)))
    return bytes(header) + b"".join(rows)

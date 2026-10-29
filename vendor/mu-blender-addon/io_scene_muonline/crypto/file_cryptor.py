# -*- coding: utf-8 -*-
"""FileCryptor —— 对应 TS 工程 src/crypto/file-cryptor.ts 与 C# FileCryptor.cs。

算法(滚动 XOR + 加法):
    mapKey 初值 0x5E
    decrypt: out[i] = (src[i] ^ KEY[i&15]) - mapKey ; mapKey = src[i] + 0x3D
    encrypt: out[i] = ((src[i] + mapKey) ^ KEY[i&15]) ; mapKey = out[i] + 0x3D
"""

MAP_XOR_KEY = bytes([
    0xD1, 0x73, 0x52, 0xF6, 0xD2, 0x9A, 0xCB, 0x27,
    0x3E, 0xAF, 0x59, 0x31, 0x37, 0xB3, 0xE7, 0xA2,
])

# 部分贴图/数据表使用的 BUX XOR 掩码(xorBuxMask,与 BuxCryptor.cs 一致)
BUX_MASK = (0xFC, 0xCF, 0xAB)


def decrypt_file_cryptor(src: bytes) -> bytes:
    """FileCryptor 解密。返回与 src 等长的明文。"""
    out = bytearray(len(src))
    map_key = 0x5E
    for i, s in enumerate(src):
        out[i] = ((s ^ MAP_XOR_KEY[i & 15]) - map_key) & 0xFF
        map_key = (s + 0x3D) & 0xFF
    return bytes(out)


def encrypt_file_cryptor(src: bytes) -> bytes:
    """FileCryptor 加密(OBJWriter/地形导出用)。"""
    out = bytearray(len(src))
    map_key = 0x5E
    for i, s in enumerate(src):
        enc = ((s + map_key) & 0xFF) ^ MAP_XOR_KEY[i & 15]
        out[i] = enc
        map_key = (enc + 0x3D) & 0xFF
    return bytes(out)


def xor_bux_mask(data: bytes) -> bytes:
    """对数据按 3 字节周期 XOR BUX 掩码(ATT 解析后使用)。"""
    out = bytearray(len(data))
    for i, b in enumerate(data):
        out[i] = b ^ BUX_MASK[i % 3]
    return bytes(out)

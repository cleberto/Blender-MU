# -*- coding: utf-8 -*-
"""LEA-256 ECB 解密 —— 对应 TS 工程 src/crypto/lea256.ts(1:1 移植,KISA 参考实现,小端)。

用于 BMD v15 的加密区解密。
LEA 是 128 位分组、256 位密钥、32 轮的 ARX 密码。
"""

KEY_DELTA = [
    0xC3EFE9DB, 0x44626B02, 0x79E27C8A, 0x78DF30EC,
    0x715EA49E, 0xC785DA0A, 0xE04EF22A, 0xE5C40957,
]

_MASK32 = 0xFFFFFFFF


def _rol(x, n):
    n &= 31
    return ((x << n) | (x >> (32 - n))) & _MASK32


def _ror(x, n):
    n &= 31
    return ((x >> n) | (x << (32 - n))) & _MASK32


def _key_schedule_256(key_words):
    rk = [0] * 192
    t = list(key_words)
    for i in range(32):
        d = KEY_DELTA[i & 7]
        s = (i * 6) & 7
        t[(s + 0) & 7] = _rol((t[(s + 0) & 7] + _rol(d, i)) & _MASK32, 1)
        t[(s + 1) & 7] = _rol((t[(s + 1) & 7] + _rol(d, i + 1)) & _MASK32, 3)
        t[(s + 2) & 7] = _rol((t[(s + 2) & 7] + _rol(d, i + 2)) & _MASK32, 6)
        t[(s + 3) & 7] = _rol((t[(s + 3) & 7] + _rol(d, i + 3)) & _MASK32, 11)
        t[(s + 4) & 7] = _rol((t[(s + 4) & 7] + _rol(d, i + 4)) & _MASK32, 13)
        t[(s + 5) & 7] = _rol((t[(s + 5) & 7] + _rol(d, i + 5)) & _MASK32, 17)
        rk[i * 6:(i + 1) * 6] = [
            t[(s + 0) & 7], t[(s + 1) & 7], t[(s + 2) & 7],
            t[(s + 3) & 7], t[(s + 4) & 7], t[(s + 5) & 7],
        ]
    return rk


def _round_dec(s, rk6):
    # NOTE: mirrors the TS/JS reference exactly. In JS, `a - b ^ c` parses as
    # `(a - b) ^ c` ('-' binds tighter than '^'), so rk6[1] is XORed with the
    # whole subtraction result, not just with (t0 ^ rk6[0]).
    t = [0, 0, 0, 0]
    t[0] = s[3]
    t[1] = ((_ror(s[0], 9) - (t[0] ^ rk6[0])) ^ rk6[1]) & _MASK32
    t[2] = ((_rol(s[1], 5) - (t[1] ^ rk6[2])) ^ rk6[3]) & _MASK32
    t[3] = ((_rol(s[2], 3) - (t[2] ^ rk6[4])) ^ rk6[5]) & _MASK32
    return t


def create_lea256_ecb_decrypt(key):
    """key: bytes(32) → 返回 decrypt(cipher: bytes) -> bytes(明文,长度须为 16 倍数)。"""
    if len(key) != 32:
        raise ValueError("LEA-256 key must be 32 bytes")

    key_words = []
    for i in range(8):
        key_words.append(
            (key[i * 4 + 3] << 24) | (key[i * 4 + 2] << 16) |
            (key[i * 4 + 1] << 8) | key[i * 4]
        )

    rk = _key_schedule_256(key_words)
    rk6 = [0] * 6

    def decrypt_ecb(cipher):
        if len(cipher) % 16 != 0:
            raise ValueError("LEA-ECB: data length must be a multiple of 16 B")
        out = bytearray(cipher)
        for off in range(0, len(out), 16):
            state = [
                int.from_bytes(out[off + i * 4: off + i * 4 + 4], "little")
                for i in range(4)
            ]
            for r in range(32):
                rk6[:] = rk[(31 - r) * 6:(32 - r) * 6]
                state = _round_dec(state, rk6)
            for i in range(4):
                out[off + i * 4: off + i * 4 + 4] = state[i].to_bytes(4, "little")
        return bytes(out)

    return decrypt_ecb


# 与 bmd-loader.ts 相同的固定密钥
LEA_KEY = bytes([
    0xCC, 0x50, 0x45, 0x13, 0xC2, 0xA6, 0x57, 0x4E,
    0xD6, 0x9A, 0x45, 0x89, 0xBF, 0x2F, 0xBC, 0xD9,
    0x39, 0xB3, 0xB3, 0xBD, 0x50, 0xBD, 0xCC, 0xB6,
    0x85, 0x46, 0xD1, 0xD6, 0x16, 0x54, 0xE0, 0x87,
])

_lea_decrypt = create_lea256_ecb_decrypt(LEA_KEY)


def decrypt_lea256(data: bytes) -> bytes:
    """使用固定游戏密钥解密 BMD v15 数据。"""
    return _lea_decrypt(data)

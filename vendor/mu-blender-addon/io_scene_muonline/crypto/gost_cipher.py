# -*- coding: utf-8 -*-
"""GOST 28147-89 block cipher - decryption only (ported from gost-cipher.ts)."""

_MASK32 = 0xFFFFFFFF

_SBOX = [
    [4, 10, 9, 2, 13, 8, 0, 14, 6, 11, 1, 12, 7, 15, 5, 3],
    [14, 11, 4, 12, 6, 13, 15, 10, 2, 3, 8, 1, 0, 7, 5, 9],
    [5, 8, 1, 13, 10, 3, 4, 2, 14, 15, 12, 7, 6, 0, 9, 11],
    [7, 13, 10, 1, 0, 8, 9, 15, 14, 4, 6, 12, 11, 2, 5, 3],
    [6, 12, 7, 1, 5, 15, 13, 8, 4, 10, 9, 14, 0, 3, 11, 2],
    [4, 11, 10, 0, 7, 2, 1, 13, 3, 6, 8, 5, 9, 12, 15, 14],
    [13, 11, 4, 1, 3, 15, 5, 9, 0, 10, 14, 7, 6, 8, 2, 12],
    [1, 15, 13, 0, 5, 7, 10, 4, 9, 2, 3, 14, 6, 11, 8, 12],
]

_LOOKUP = []
for _k in range(4):
    _table = [0] * 256
    _s_low = _SBOX[2 * _k]
    _s_high = _SBOX[2 * _k + 1]
    for _i in range(256):
        _lo = _s_low[_i & 0x0F]
        _hi = _s_high[(_i >> 4) & 0x0F]
        _table[_i] = (_lo | (_hi << 4)) << (8 * _k)
    _LOOKUP.append(_table)


def _sbox_substitute(value):
    return (_LOOKUP[0][value & 0xFF] |
            _LOOKUP[1][(value >> 8) & 0xFF] |
            _LOOKUP[2][(value >> 16) & 0xFF] |
            _LOOKUP[3][(value >> 24) & 0xFF]) & _MASK32


def _rotl11(x):
    return ((x << 11) | (x >> 21)) & _MASK32


class GOSTCipher:
    """GOST 28147-89 block cipher (8-byte blocks), decryption only."""

    BLOCK_SIZE = 8
    ROUNDS = 32

    def __init__(self, key):
        self.block_size = GOSTCipher.BLOCK_SIZE
        k = bytes(key)[:32]
        K = [int.from_bytes(k[i * 4:i * 4 + 4], 'little') for i in range(8)]
        self.decrypt_schedule = [0] * GOSTCipher.ROUNDS
        for i in range(8):
            self.decrypt_schedule[i] = K[i]
        for rep in range(3):
            for i in range(8):
                self.decrypt_schedule[8 + rep * 8 + i] = K[7 - i]

    def get_block_size(self):
        return self.block_size

    def block_decrypt(self, data, length, out):
        for i in range(0, length, self.block_size):
            self._decrypt_block(data, i, out, i)

    def _decrypt_block(self, src, src_off, dst, dst_off):
        n1 = int.from_bytes(src[src_off:src_off + 4], 'little')
        n2 = int.from_bytes(src[src_off + 4:src_off + 8], 'little')
        ks = self.decrypt_schedule

        for i in range(31):
            temp = (n1 + ks[i]) & _MASK32
            rotated = _rotl11(_sbox_substitute(temp))
            new_n1 = (n2 ^ rotated) & _MASK32
            n2 = n1
            n1 = new_n1

        temp = (n1 + ks[31]) & _MASK32
        rotated = _rotl11(_sbox_substitute(temp))
        n2 = (n2 ^ rotated) & _MASK32

        dst[dst_off:dst_off + 4] = n1.to_bytes(4, 'little')
        dst[dst_off + 4:dst_off + 8] = n2.to_bytes(4, 'little')

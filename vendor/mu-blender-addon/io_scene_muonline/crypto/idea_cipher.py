# -*- coding: utf-8 -*-
"""IDEA block cipher - decryption only (ported from idea-cipher.ts)."""


def _mul_mod(a, b):
    a &= 0xFFFF
    b &= 0xFFFF
    if a == 0:
        a = 0x10000
    if b == 0:
        b = 0x10000
    r = (a * b) % 0x10001
    return 0 if r == 0x10000 else r & 0xFFFF


def _add_mod(a, b):
    return (a + b) & 0xFFFF


def _mul_inverse(x):
    x &= 0xFFFF
    if x <= 1:
        return x
    t1 = 0x10001 // x
    y = 0x10001 % x
    if y == 1:
        return (0x10001 - t1) & 0xFFFF
    t0 = 1
    while y != 1:
        q = x // y
        x = x % y
        t0 = (t0 + q * t1) % 0x10001
        if x == 1:
            return t0 & 0xFFFF
        q2 = y // x
        y = y % x
        t1 = (t1 + q2 * t0) % 0x10001
    return (0x10001 - t1) & 0xFFFF


def _add_inverse(x):
    return (0x10000 - (x & 0xFFFF)) & 0xFFFF


def _expand_key(key):
    Z = [0] * 52
    for i in range(8):
        Z[i] = int.from_bytes(key[i * 2:i * 2 + 2], 'big')
    for i in range(8, 52):
        if (i & 7) == 6:
            Z[i] = ((Z[i - 7] << 9) | (Z[i - 14] >> 7)) & 0xFFFF
        elif (i & 7) == 7:
            Z[i] = ((Z[i - 15] << 9) | (Z[i - 14] >> 7)) & 0xFFFF
        else:
            Z[i] = ((Z[i - 7] << 9) | (Z[i - 6] >> 7)) & 0xFFFF
    return Z


def _invert_keys(enc):
    dec = [0] * 52
    p = 0
    q = 52

    t1 = _mul_inverse(enc[p]); p += 1
    t2 = _add_inverse(enc[p]); p += 1
    t3 = _add_inverse(enc[p]); p += 1
    t4 = _mul_inverse(enc[p]); p += 1
    q -= 1; dec[q] = t4
    q -= 1; dec[q] = t3
    q -= 1; dec[q] = t2
    q -= 1; dec[q] = t1

    for _r in range(1, 8):
        t1 = enc[p]; p += 1
        t2 = enc[p]; p += 1
        q -= 1; dec[q] = t2
        q -= 1; dec[q] = t1

        t1 = _mul_inverse(enc[p]); p += 1
        t2 = _add_inverse(enc[p]); p += 1
        t3 = _add_inverse(enc[p]); p += 1
        t4 = _mul_inverse(enc[p]); p += 1
        q -= 1; dec[q] = t4
        q -= 1; dec[q] = t2
        q -= 1; dec[q] = t3
        q -= 1; dec[q] = t1

    t1 = enc[p]; p += 1
    t2 = enc[p]; p += 1
    q -= 1; dec[q] = t2
    q -= 1; dec[q] = t1

    t1 = _mul_inverse(enc[p]); p += 1
    t2 = _add_inverse(enc[p]); p += 1
    t3 = _add_inverse(enc[p]); p += 1
    t4 = _mul_inverse(enc[p]); p += 1
    q -= 1; dec[q] = t4
    q -= 1; dec[q] = t3
    q -= 1; dec[q] = t2
    q -= 1; dec[q] = t1

    return dec


class IDEACipher:
    """IDEA block cipher (8-byte blocks), decryption only."""

    BLOCK_SIZE = 8
    ROUNDS = 8

    def __init__(self, key):
        self.block_size = IDEACipher.BLOCK_SIZE
        self.decrypt_keys = _invert_keys(_expand_key(bytes(key)[:16]))

    def get_block_size(self):
        return self.block_size

    def block_decrypt(self, data, length, out):
        for i in range(0, length, self.block_size):
            self._decrypt_block(data, i, out, i)

    def _decrypt_block(self, src, src_off, dst, dst_off):
        K = self.decrypt_keys
        x0 = int.from_bytes(src[src_off:src_off + 2], 'big')
        x1 = int.from_bytes(src[src_off + 2:src_off + 4], 'big')
        x2 = int.from_bytes(src[src_off + 4:src_off + 6], 'big')
        x3 = int.from_bytes(src[src_off + 6:src_off + 8], 'big')
        p = 0

        for _round in range(IDEACipher.ROUNDS):
            x0 = _mul_mod(x0, K[p]); p += 1
            x1 = _add_mod(x1, K[p]); p += 1
            x2 = _add_mod(x2, K[p]); p += 1
            x3 = _mul_mod(x3, K[p]); p += 1

            t0 = x1
            t1 = x2
            x2 = x2 ^ x0
            x1 = x1 ^ x3

            x2 = _mul_mod(x2, K[p]); p += 1
            x1 = _add_mod(x1, x2)
            x1 = _mul_mod(x1, K[p]); p += 1
            x2 = _add_mod(x2, x1)

            x0 = x0 ^ x1
            x3 = x3 ^ x2
            x1 = x1 ^ t1
            x2 = x2 ^ t0

        X1 = _mul_mod(x0, K[p]); p += 1
        X2 = _add_mod(x2, K[p]); p += 1
        X3 = _add_mod(x1, K[p]); p += 1
        X4 = _mul_mod(x3, K[p]); p += 1

        dst[dst_off:dst_off + 2] = X1.to_bytes(2, 'big')
        dst[dst_off + 2:dst_off + 4] = X2.to_bytes(2, 'big')
        dst[dst_off + 4:dst_off + 6] = X3.to_bytes(2, 'big')
        dst[dst_off + 6:dst_off + 8] = X4.to_bytes(2, 'big')

# -*- coding: utf-8 -*-
"""ThreeWay block cipher - decryption only (ported from threeway-cipher.ts)."""

_MASK32 = 0xFFFFFFFF


def _rotl(x, n):
    n &= 31
    return ((x << n) | (x >> (32 - n))) & _MASK32


def _reverse_bytes(x):
    return (((x & 0x000000FF) << 24) |
            ((x & 0x0000FF00) << 8) |
            ((x & 0x00FF0000) >> 8) |
            ((x & 0xFF000000) >> 24)) & _MASK32


def _reverse_bits(a):
    a = (((a & 0xAAAAAAAA) >> 1) | ((a & 0x55555555) << 1)) & _MASK32
    a = (((a & 0xCCCCCCCC) >> 2) | ((a & 0x33333333) << 2)) & _MASK32
    return (((a & 0xF0F0F0F0) >> 4) | ((a & 0x0F0F0F0F) << 4)) & _MASK32


def _theta(t):
    c0 = (t['a0'] ^ t['a1'] ^ t['a2']) & _MASK32
    c = (_rotl(c0, 16) ^ _rotl(c0, 8)) & _MASK32
    b0 = (((t['a0'] << 24) ^ (t['a2'] >> 8) ^ (t['a1'] << 8) ^ (t['a0'] >> 24))) & _MASK32
    b1 = (((t['a1'] << 24) ^ (t['a0'] >> 8) ^ (t['a2'] << 8) ^ (t['a1'] >> 24))) & _MASK32
    t['a0'] = (t['a0'] ^ c ^ b0) & _MASK32
    t['a1'] = (t['a1'] ^ c ^ b1) & _MASK32
    t['a2'] = (t['a2'] ^ c ^ ((b0 >> 16) ^ (b1 << 16))) & _MASK32


def _mu(t):
    t['a1'] = _reverse_bits(t['a1'])
    tmp = _reverse_bits(t['a0'])
    t['a0'] = _reverse_bits(t['a2'])
    t['a2'] = tmp


def _pi_gamma_pi(t):
    b2 = _rotl(t['a2'], 1)
    b0 = _rotl(t['a0'], 22)
    t['a0'] = _rotl((b0 ^ (t['a1'] | ((~b2) & _MASK32))) & _MASK32, 1)
    t['a2'] = _rotl((b2 ^ (b0 | ((~t['a1']) & _MASK32))) & _MASK32, 22)
    t['a1'] = (t['a1'] ^ (b2 | ((~b0) & _MASK32))) & _MASK32


def _rho(t):
    _theta(t)
    _pi_gamma_pi(t)


class ThreeWayCipher:
    """ThreeWay block cipher (12-byte blocks), decryption only."""

    BLOCK_SIZE = 12
    ROUNDS = 11
    START_D = 0xB1B1

    def __init__(self, key):
        self.block_size = ThreeWayCipher.BLOCK_SIZE
        k = bytes(key)[:12]
        self.k = [0] * 3
        for i in range(3):
            self.k[i] = ((k[4 * i + 3] |
                          (k[4 * i + 2] << 8) |
                          (k[4 * i + 1] << 16) |
                          (k[4 * i] << 24))) & _MASK32
        tk = {'a0': self.k[0], 'a1': self.k[1], 'a2': self.k[2]}
        _theta(tk)
        _mu(tk)
        self.k[0] = _reverse_bytes(tk['a0'])
        self.k[1] = _reverse_bytes(tk['a1'])
        self.k[2] = _reverse_bytes(tk['a2'])

    def get_block_size(self):
        return self.block_size

    def block_decrypt(self, data, length, out):
        for i in range(0, length, self.block_size):
            self._decrypt_block(data, i, out, i)

    def _decrypt_block(self, in_buf, in_off, out_buf, out_off):
        t = {
            'a0': int.from_bytes(in_buf[in_off:in_off + 4], 'little'),
            'a1': int.from_bytes(in_buf[in_off + 4:in_off + 8], 'little'),
            'a2': int.from_bytes(in_buf[in_off + 8:in_off + 12], 'little'),
        }
        rc = ThreeWayCipher.START_D
        _mu(t)

        for _i in range(ThreeWayCipher.ROUNDS):
            t['a0'] = (t['a0'] ^ self.k[0] ^ ((rc << 16) & _MASK32)) & _MASK32
            t['a1'] = (t['a1'] ^ self.k[1]) & _MASK32
            t['a2'] = (t['a2'] ^ self.k[2] ^ rc) & _MASK32
            _rho(t)
            rc = (rc << 1) & _MASK32
            if rc & 0x10000:
                rc ^= 0x11011
            rc &= 0xFFFF

        t['a0'] = (t['a0'] ^ self.k[0] ^ ((rc << 16) & _MASK32)) & _MASK32
        t['a1'] = (t['a1'] ^ self.k[1]) & _MASK32
        t['a2'] = (t['a2'] ^ self.k[2] ^ rc) & _MASK32
        _theta(t)
        _mu(t)

        out_buf[out_off:out_off + 4] = t['a0'].to_bytes(4, 'little')
        out_buf[out_off + 4:out_off + 8] = t['a1'].to_bytes(4, 'little')
        out_buf[out_off + 8:out_off + 12] = t['a2'].to_bytes(4, 'little')

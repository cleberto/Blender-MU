# -*- coding: utf-8 -*-
"""小端二进制读写工具 —— 对应 TS 工程 src/BinaryStruct.ts 的 StructLayout 思想。

提供:
    BinaryReader  —— 顺序读取 s8/u8/s16/u16/s32/u32/f32/f64/定长字符串/结构体数组
    BinaryWriter  —— 顺序写入
纯 Python,不依赖 bpy,可单测。
"""

import struct


class BinaryReader:
    def __init__(self, data: bytes, offset: int = 0):
        self._data = data
        self._off = offset

    @property
    def offset(self):
        return self._off

    @offset.setter
    def offset(self, value):
        self._off = value

    @property
    def remaining(self):
        return len(self._data) - self._off

    def _need(self, n):
        if self._off + n > len(self._data):
            raise EOFError(
                f"BinaryReader: need {n} bytes at offset {self._off}, "
                f"only {len(self._data) - self._off} left"
            )

    def read(self, n):
        self._need(n)
        out = self._data[self._off:self._off + n]
        self._off += n
        return out

    def read_u8(self):
        self._need(1)
        v = self._data[self._off]
        self._off += 1
        return v

    def read_s8(self):
        self._need(1)
        v = self._data[self._off]
        self._off += 1
        return v - 256 if v >= 128 else v

    def read_u16(self):
        self._need(2)
        v = struct.unpack_from("<H", self._data, self._off)[0]
        self._off += 2
        return v

    def read_s16(self):
        self._need(2)
        v = struct.unpack_from("<h", self._data, self._off)[0]
        self._off += 2
        return v

    def read_u32(self):
        self._need(4)
        v = struct.unpack_from("<I", self._data, self._off)[0]
        self._off += 4
        return v

    def read_s32(self):
        self._need(4)
        v = struct.unpack_from("<i", self._data, self._off)[0]
        self._off += 4
        return v

    def read_f32(self):
        self._need(4)
        v = struct.unpack_from("<f", self._data, self._off)[0]
        self._off += 4
        return v

    def read_f64(self):
        self._need(8)
        v = struct.unpack_from("<d", self._data, self._off)[0]
        self._off += 8
        return v

    def read_bool(self):
        return self.read_u8() != 0

    def read_fixed_string(self, length):
        """读取定长 ASCII 字符串,截断到首个 NUL。"""
        raw = self.read(length)
        zero = raw.find(b"\x00")
        if zero != -1:
            raw = raw[:zero]
        return raw.decode("ascii", errors="replace")

    def read_vec3(self):
        return (self.read_f32(), self.read_f32(), self.read_f32())

    def read_vec3_f64(self):
        return (self.read_f64(), self.read_f64(), self.read_f64())

    def read_struct_array(self, count, field_layout):
        """读取 count 个结构体。field_layout: [(name, fmt)] fmt 为
        's8'|'u8'|'s16'|'u16'|'s32'|'u32'|'f32'|'f64'。返回 dict 列表。"""
        out = []
        for _ in range(count):
            rec = {}
            for name, fmt in field_layout:
                rec[name] = getattr(self, "read_" + fmt)()
            out.append(rec)
        return out


class BinaryWriter:
    def __init__(self):
        self._parts = []

    def write(self, data: bytes):
        self._parts.append(bytes(data))

    def write_u8(self, v):
        self._parts.append(struct.pack("<B", v & 0xFF))

    def write_s8(self, v):
        self._parts.append(struct.pack("<b", v))

    def write_u16(self, v):
        self._parts.append(struct.pack("<H", v & 0xFFFF))

    def write_s16(self, v):
        self._parts.append(struct.pack("<h", v))

    def write_u32(self, v):
        self._parts.append(struct.pack("<I", v & 0xFFFFFFFF))

    def write_s32(self, v):
        self._parts.append(struct.pack("<i", v))

    def write_f32(self, v):
        self._parts.append(struct.pack("<f", v))

    def write_f64(self, v):
        self._parts.append(struct.pack("<d", v))

    def write_bool(self, v):
        self.write_u8(1 if v else 0)

    def write_fixed_string(self, s, length):
        raw = s.encode("ascii", errors="replace")[:length]
        raw = raw.ljust(length, b"\x00")
        self._parts.append(raw)

    def write_vec3(self, v):
        self.write_f32(v[0])
        self.write_f32(v[1])
        self.write_f32(v[2])

    def write_struct_array(self, records, field_layout):
        for rec in records:
            for name, fmt in field_layout:
                getattr(self, "write_" + fmt)(rec[name])

    def getvalue(self):
        return b"".join(self._parts)

# -*- coding: utf-8 -*-
"""BMD model format - reader/writer.

Mirrors src/bmd-loader.ts (parse) + src/types.ts (data structures) in the
TypeScript muonline-bmd-viewer project.

BMD file layout:
    [0..3]   "BMD" + version
    v12:     [4..7] size(i32); [8..8+size] FileCryptor-encrypted region.
             The decrypted region IS the real data starting with the name.
    v15:     same, but LEA-256-ECB.
    header:  name(32) | meshCount(u16) | boneCount(u16) | actionCount(u16)
    meshes xN, actions xN, bones xN (see readers below)

This module has no bpy dependency and can be unit-tested standalone.
"""

from dataclasses import dataclass, field

from .binary import BinaryReader, BinaryWriter
from ..crypto.file_cryptor import decrypt_file_cryptor, encrypt_file_cryptor
from ..crypto.lea256 import decrypt_lea256

MAGIC = b"BMD"
STRING_LENGTH = 32
TRIANGLE_STRIDE = 64


# ---------------------------------------------------------------- structures


@dataclass
class BMDBoneMatrix:
    positions: list = field(default_factory=list)      # [(x,y,z), ...]
    rotations: list = field(default_factory=list)      # [(x,y,z), ...] euler
    quaternions: list = field(default_factory=list)    # [(x,y,z,w), ...]


@dataclass
class BMDTextureBone:
    name: str = ""
    parent: int = -1
    is_dummy: bool = False
    matrixes: list = field(default_factory=list)       # [BMDBoneMatrix] per action


@dataclass
class BMDTextureAction:
    num_animation_keys: int = 0
    lock_positions: bool = False
    positions: list = field(default_factory=list)      # [(x,y,z), ...]


@dataclass
class BMDTriangle:
    polygon: int = 3
    vertex_index: list = field(default_factory=lambda: [0, 0, 0, 0])
    normal_index: list = field(default_factory=lambda: [0, 0, 0, 0])
    tex_coord_index: list = field(default_factory=lambda: [0, 0, 0, 0])


@dataclass
class BMDTextureMesh:
    texture: int = 0
    num_vertices: int = 0
    num_normals: int = 0
    num_tex_coords: int = 0
    num_triangles: int = 0
    vertices: list = field(default_factory=list)       # [(node, (x,y,z))]
    normals: list = field(default_factory=list)        # [(node, (x,y,z), bindVertex)]
    tex_coords: list = field(default_factory=list)     # [(u,v)]
    triangles: list = field(default_factory=list)      # [BMDTriangle]
    texture_path: str = ""


@dataclass
class BMDData:
    version: int = 0
    name: str = ""
    meshes: list = field(default_factory=list)
    bones: list = field(default_factory=list)
    actions: list = field(default_factory=list)


# ---------------------------------------------------------------- helpers


def bmd_angle_to_quaternion(euler):
    """Euler(radians) -> quaternion(x,y,z,w).

    1:1 port of bmdAngleToQuaternion in bmd-loader.ts (custom internal formula,
    not Three.js default order).
    """
    import math
    x, y, z = euler
    half_x, half_y, half_z = x * 0.5, y * 0.5, z * 0.5
    sin_x, cos_x = math.sin(half_x), math.cos(half_x)
    sin_y, cos_y = math.sin(half_y), math.cos(half_y)
    sin_z, cos_z = math.sin(half_z), math.cos(half_z)

    w = cos_x * cos_y * cos_z + sin_x * sin_y * sin_z
    qx = sin_x * cos_y * cos_z - cos_x * sin_y * sin_z
    qy = cos_x * sin_y * cos_z + sin_x * cos_y * sin_z
    qz = cos_x * cos_y * sin_z - sin_x * sin_y * cos_z
    n = (w * w + qx * qx + qy * qy + qz * qz) ** 0.5
    if n == 0:
        return (0.0, 0.0, 0.0, 1.0)
    return (qx / n, qy / n, qz / n, w / n)


def quaternion_to_bmd_angle(q):
    """Quaternion -> euler(radians), inverse of bmd_angle_to_quaternion."""
    import math
    x, y, z, w = q
    sin_y = max(-1.0, min(1.0, 2.0 * (w * y - x * z)))
    yaw = math.asin(sin_y)
    if abs(sin_y) < 0.9999999:
        pitch = math.atan2(2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y))
        roll = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))
    else:
        # Gimbal-lock branch: sign must match the custom forward formula so
        # that euler -> quaternion round-trips exactly (a wrong sign maps a
        # ~180 deg rotation to a different one, displacing child bones).
        pitch = math.atan2(2.0 * (w * x - y * z), 1.0 - 2.0 * (x * x + z * z))
        roll = 0.0
    return (pitch, yaw, roll)


# ---------------------------------------------------------------- parse


def _read_encrypted(data):
    """Read BMD, handling v12/v15 encryption. Returns (work, version, dataOffset)."""
    if len(data) < 4:
        raise ValueError("BMD: buffer too small")
    if data[:3] != MAGIC:
        raise ValueError(f"BMD: invalid header {data[:3]!r}")
    version = data[3]
    work = bytearray(data)
    data_offset = 4
    if version in (12, 15):
        size = int.from_bytes(work[4:8], "little")
        enc = bytes(work[8:8 + size])
        dec = decrypt_file_cryptor(enc) if version == 12 else decrypt_lea256(enc)
        work[4:4 + size] = dec
        data_offset = 4
    return work, version, data_offset


def _read_mesh(br):
    num_vertices = br.read_s16()
    num_normals = br.read_s16()
    num_tex_coords = br.read_s16()
    num_triangles = br.read_s16()
    texture = br.read_s16()

    vertices = []
    for _ in range(num_vertices):
        node = br.read_s16()
        br.read_s16()  # padding
        x, y, z = br.read_vec3()
        vertices.append((node, (x, y, z)))

    normals = []
    for _ in range(num_normals):
        node = br.read_s16()
        br.read_s16()  # padding
        nx, ny, nz = br.read_vec3()
        bind_vertex = br.read_s16()
        br.read_s16()  # padding
        normals.append((node, (nx, ny, nz), bind_vertex))

    tex_coords = []
    for _ in range(num_tex_coords):
        tex_coords.append((br.read_f32(), br.read_f32()))

    triangles = []
    for _ in range(num_triangles):
        start = br.offset
        polygon = br.read_u8()
        br.read(1)  # padding
        v_idx = [br.read_s16() for _ in range(4)]
        n_idx = [br.read_s16() for _ in range(4)]
        t_idx = [br.read_s16() for _ in range(4)]
        # lightMapCoord(32B) + lightMapIndexes(2B) + pad -> stride 64B
        br.offset = start + TRIANGLE_STRIDE
        triangles.append(BMDTriangle(polygon, v_idx, n_idx, t_idx))

    texture_path = br.read_fixed_string(STRING_LENGTH)

    return BMDTextureMesh(
        texture=texture,
        num_vertices=num_vertices,
        num_normals=num_normals,
        num_tex_coords=num_tex_coords,
        num_triangles=num_triangles,
        vertices=vertices,
        normals=normals,
        tex_coords=tex_coords,
        triangles=triangles,
        texture_path=texture_path,
    )


def _read_action(br):
    num_keys = br.read_s16()
    lock_positions = br.read_bool()
    positions = [br.read_vec3() for _ in range(num_keys)] if lock_positions else []
    return BMDTextureAction(num_animation_keys=num_keys,
                            lock_positions=lock_positions,
                            positions=positions)


def _read_bone(br, actions, bind_pose_only=False):
    is_dummy = br.read_bool()
    if is_dummy:
        return BMDTextureBone(name="", parent=-1, is_dummy=True, matrixes=[])

    name = br.read_fixed_string(STRING_LENGTH)
    parent = br.read_s16()
    bone = BMDTextureBone(name=name, parent=parent, is_dummy=False, matrixes=[])

    for a in range(len(actions)):
        act = actions[a]
        keys = act.num_animation_keys
        mat = BMDBoneMatrix()
        if keys == 0:
            bone.matrixes.append(mat)
            continue

        if bind_pose_only:
            if a == 0:
                pos0 = br.read_vec3()
                br.read((keys - 1) * 12)
                rot0 = br.read_vec3()
                br.read((keys - 1) * 12)
                mat.positions = [pos0]
                mat.rotations = [rot0]
                mat.quaternions = [bmd_angle_to_quaternion(rot0)]
            else:
                br.read(keys * 12 * 2)
            bone.matrixes.append(mat)
            continue

        mat.positions = [br.read_vec3() for _ in range(keys)]
        mat.rotations = [br.read_vec3() for _ in range(keys)]
        mat.quaternions = [bmd_angle_to_quaternion(r) for r in mat.rotations]
        bone.matrixes.append(mat)

    return bone


def parse_bmd(data, bind_pose_only=False):
    """Parse BMD bytes into BMDData.

    With bind_pose_only=True only frame 0 of action 0 is read per bone
    (fast path for bind-pose preview).
    """
    work, version, data_offset = _read_encrypted(data)
    br = BinaryReader(bytes(work), data_offset)

    name = br.read_fixed_string(STRING_LENGTH)
    mesh_count = br.read_u16()
    bone_count = br.read_u16()
    action_count = br.read_u16()

    bmd = BMDData(version=version, name=name)

    for _ in range(mesh_count):
        bmd.meshes.append(_read_mesh(br))
    for _ in range(action_count):
        bmd.actions.append(_read_action(br))
    for _ in range(bone_count):
        bmd.bones.append(_read_bone(br, bmd.actions, bind_pose_only=bind_pose_only))

    return bmd


# ---------------------------------------------------------------- write


def _write_mesh(br, mesh):
    br.write_s16(mesh.num_vertices)
    br.write_s16(mesh.num_normals)
    br.write_s16(mesh.num_tex_coords)
    br.write_s16(mesh.num_triangles)
    br.write_s16(mesh.texture)

    for node, (x, y, z) in mesh.vertices:
        br.write_s16(node)
        br.write_s16(0)
        br.write_f32(x)
        br.write_f32(y)
        br.write_f32(z)

    for node, (nx, ny, nz), bind_vertex in mesh.normals:
        br.write_s16(node)
        br.write_s16(0)
        br.write_f32(nx)
        br.write_f32(ny)
        br.write_f32(nz)
        br.write_s16(bind_vertex)
        br.write_s16(0)

    for u, v in mesh.tex_coords:
        br.write_f32(u)
        br.write_f32(v)

    for tri in mesh.triangles:
        br.write_u8(tri.polygon)
        br.write_u8(0)  # padding
        for i in range(4):
            br.write_s16(tri.vertex_index[i])
        for i in range(4):
            br.write_s16(tri.normal_index[i])
        for i in range(4):
            br.write_s16(tri.tex_coord_index[i])
        br.write(b"\x00" * 32)  # lightMapCoord
        br.write_s16(0)          # lightMapIndexes
        br.write(b"\x00" * 4)    # padding -> 64B

    br.write_fixed_string(mesh.texture_path, STRING_LENGTH)


def _write_action(br, action):
    br.write_s16(action.num_animation_keys)
    br.write_bool(action.lock_positions)
    if action.lock_positions:
        for p in action.positions:
            br.write_vec3(p)


def _write_bone(br, bone):
    br.write_bool(bone.is_dummy)
    if bone.is_dummy:
        return
    br.write_fixed_string(bone.name, STRING_LENGTH)
    br.write_s16(bone.parent)
    for mat in bone.matrixes:
        keys = len(mat.positions)
        for k in range(keys):
            br.write_vec3(mat.positions[k])
        for k in range(keys):
            br.write_vec3(mat.rotations[k] if k < len(mat.rotations) else (0, 0, 0))


def write_bmd(bmd, version=12):
    """Serialize BMDData. version=12 -> FileCryptor; other versions plaintext."""
    br = BinaryWriter()
    br.write(MAGIC)
    br.write_u8(version)
    if version in (12, 15):
        br.write_u32(0)  # size placeholder

    br.write_fixed_string(bmd.name, STRING_LENGTH)
    br.write_u16(len(bmd.meshes))
    br.write_u16(len(bmd.bones))
    br.write_u16(len(bmd.actions))

    for mesh in bmd.meshes:
        _write_mesh(br, mesh)
    for action in bmd.actions:
        _write_action(br, action)
    for bone in bmd.bones:
        _write_bone(br, bone)

    plain = br.getvalue()
    if version in (12, 15):
        # Official layout: [0:4]="BMD"+ver, [4:8]=region length, [8:8+size]=region.
        # The encrypted region plaintext starts with the name (skip 4-byte placeholder).
        payload = plain[8:]
        if version == 12:
            enc = encrypt_file_cryptor(payload)
        else:
            enc = _encrypt_lea256(payload)
        header = plain[:4] + len(enc).to_bytes(4, "little")
        return header + enc
    return plain


def _encrypt_lea256(payload):
    """LEA-256 encryption (ECB). Official v15 export is uncommon; not implemented."""
    raise NotImplementedError(
        "BMD v15 (LEA-256) export is not implemented; use version=12 or plaintext."
    )

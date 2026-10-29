# -*- coding: utf-8 -*-
"""数学工具 —— 对应 bmd-loader.ts 中的 bmdAngleToQuaternion 与坐标系约定。

MU 世界为 Z 向上、XY 地面。Blender 默认为 Z 向上,因此导入时可直接使用
游戏坐标;但为与参考查看器(Y-up)对齐保持一致观感,提供轴转换助手。
"""

import math


def bmd_angle_to_quaternion(euler):
    """欧拉(弧度) → 四元数(x,y,z,w),1:1 移植 TS bmdAngleToQuaternion。"""
    x, y, z = euler
    hx, hy, hz = x * 0.5, y * 0.5, z * 0.5
    sx, cx = math.sin(hx), math.cos(hx)
    sy, cy = math.sin(hy), math.cos(hy)
    sz, cz = math.sin(hz), math.cos(hz)

    w = cx * cy * cz + sx * sy * sz
    qx = sx * cy * cz - cx * sy * sz
    qy = cx * sy * cz + sx * cy * sz
    qz = cx * cy * sz - sx * sy * cz
    n = math.sqrt(w * w + qx * qx + qy * qy + qz * qz) or 1.0
    return (qx / n, qy / n, qz / n, w / n)


def quaternion_to_bmd_angle(q):
    """四元数 → 欧拉(弧度),与 bmd_angle_to_quaternion 互逆。"""
    x, y, z, w = q
    sin_y = max(-1.0, min(1.0, 2.0 * (w * y - x * z)))
    yaw = math.asin(sin_y)
    if abs(sin_y) < 0.9999999:
        pitch = math.atan2(2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y))
        roll = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))
    else:
        pitch = math.atan2(-2.0 * (w * x - y * z), 1.0 - 2.0 * (x * x + z * z))
        roll = 0.0
    return (pitch, yaw, roll)


def mu_to_blender_rotation(angle):
    """把 MU 物件角度(弧度)转换为 Blender 欧拉(弧度)。
    MU: Z-up,XY 地面;Blender: Z-up。查看器在 Y-up 中做 rotation.x=-PI/2。
    这里保持 Z-up → 直接映射(角度语义一致)。"""
    return (angle[0], angle[1], angle[2])


# 导出默认版本(官方服务器兼容性最好的 FileCryptor 加密版)
DEFAULT_BMD_EXPORT_VERSION = 12

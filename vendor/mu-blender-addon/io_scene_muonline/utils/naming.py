# -*- coding: utf-8 -*-
"""命名唯一化工具 —— 对应 bmd-loader.ts 中骨骼/网格名称唯一化逻辑。"""


def ensure_unique_name(base, used):
    """给定基础名,若已存在于 used 集合则追加 _1,_2…,返回唯一名并登记。"""
    name = base
    i = 1
    while name in used:
        name = f"{base}_{i}"
        i += 1
    used.add(name)
    return name


def sanitize_name(name, fallback="bone"):
    """过滤 Blender 非法字符(名称中不允许 ':' 等),保证非空。"""
    clean = "".join(c for c in name if c.isalnum() or c in "_-. ").strip()
    return clean or fallback

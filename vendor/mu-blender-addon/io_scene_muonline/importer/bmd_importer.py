# -*- coding: utf-8 -*-
"""BMD 模型导入 —— 把 formats.bmd.BMDData 构建为 Blender 网格/骨架/动作。

流程(镜像 bmd-loader.ts 的 BMDLoader.load):
    1. 唯一化骨骼名称 → 构建 Armature + EditBone(绑定姿态世界矩阵)
    2. 每个网格 → Mesh 对象 + 顶点组(node) + 权重 1.0 + Armature 修改器
    3. 每个动作 → 相对绑定姿态的 delta 关键帧(PoseBone.location / rotation_quaternion)
"""

import math

import bpy
import bmesh
from mathutils import Matrix, Quaternion, Vector

from ..formats.bmd import BMDData, BMDTextureMesh
from ..utils.naming import ensure_unique_name, sanitize_name

FPS = 24


# ---------------------------------------------------------------- 辅助


def _world_bind_matrices(bmd: BMDData):
    """计算每个骨骼的绑定姿态世界矩阵(4x4)。

    约定:骨骼 0..n 的父索引 = bone.parent;bind 数据取 action 0 的第 0 帧
    (与 TS 查看器一致)。返回 [Matrix, ...],并返回每个骨骼的本地 (pos, quat)。
    """
    world = []
    local = []
    for i, bone in enumerate(bmd.bones):
        if bone.is_dummy or not bone.matrixes:
            local.append((Vector((0, 0, 0)), Quaternion()))
            world.append(Matrix.Identity(4))
            continue
        mat = bone.matrixes[0]
        p = mat.positions[0] if mat.positions else (0, 0, 0)
        q = mat.quaternions[0] if mat.quaternions else (0, 0, 0, 1)
        loc = Vector((p[0], p[1], p[2]))
        quat = Quaternion((q[3], q[0], q[1], q[2]))  # Blender wxyz
        local.append((loc, quat))
        m = Matrix.LocRotScale(loc, quat, Vector((1, 1, 1)))
        parent = bone.parent
        if 0 <= parent < len(world):
            m = world[parent] @ m
        world.append(m)
    return world, local


def _tail_length(bmd: BMDData, i: int, world, scale: float):
    """为骨骼选择一个合理的尾长度(用于显示;不参与变形)。"""
    # 指向第一个子骨骼的中心
    children = [j for j, b in enumerate(bmd.bones)
                if not b.is_dummy and b.parent == i and j < len(world)]
    if children:
        avg = Vector((0, 0, 0))
        for c in children:
            avg += world[c].to_translation()
        avg /= len(children)
        d = (avg - world[i].to_translation()).length
        return max(d * 0.5 * scale, 0.1 * scale)
    return 1.0 * scale


def _build_armature(bmd: BMDData, scale: float, name: str):
    """Create the armature object. Returns (armature_obj, bone_names, world)."""
    world, local_rest = _world_bind_matrices(bmd)

    arm_data = bpy.data.armatures.new(name)
    arm_data.display_type = "OCTAHEDRAL"
    arm_obj = bpy.data.objects.new(name, arm_data)
    bpy.context.collection.objects.link(arm_obj)

    used = set()
    bone_names = []
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")

    edit_bones = []
    try:
        for i, bone in enumerate(bmd.bones):
            ebone = arm_data.edit_bones.new(sanitize_name(bone.name or f"bone_{i}"))
            ebone.name = ensure_unique_name(ebone.name, used)
            bone_names.append(ebone.name)

            if bone.is_dummy:
                ebone.head = Vector((0, 0, 0)) * scale
                ebone.tail = Vector((0, 1, 0)) * scale
            else:
                # EditBone.matrix is in armature space (parent-relative
                # head/tail/roll are derived automatically by Blender), so we
                # can feed it the world bind matrix directly.
                m = world[i].copy()
                m.translation = m.translation * scale
                ebone.length = _tail_length(bmd, i, world, scale)
                ebone.matrix = m
            edit_bones.append(ebone)

        # Parent links (armature-space matrix is preserved by .parent assignment)
        for i, bone in enumerate(bmd.bones):
            if bone.is_dummy:
                continue
            parent = bone.parent
            if 0 <= parent < len(edit_bones):
                edit_bones[i].parent = edit_bones[parent]

        bpy.ops.object.mode_set(mode="OBJECT")
    except Exception:
        bpy.ops.object.mode_set(mode="OBJECT")
        raise

    # Verify the rest pose exactly reproduces the bind pose.
    mismatch = 0
    for i, b in enumerate(arm_data.bones):
        if i >= len(world):
            continue
        wm = world[i].copy()
        wm.translation = wm.translation * scale
        dp = (b.matrix_local.to_translation() - wm.to_translation()).length
        dq = abs(1.0 - abs(b.matrix_local.to_quaternion().dot(wm.to_quaternion())))
        if dp > 1e-3 or dq > 1e-3:
            mismatch += 1
    print("[MuOnline] rest-vs-bind mismatch bones: %d/%d" % (
        mismatch, len(arm_data.bones)))

    # Store the EXACT original bone-local rest pose (BMD units) as custom
    # properties. The exporter prefers these over Blender's matrix_local
    # because EditBone head/tail/roll cannot exactly reconstruct a ~180 deg
    # rotation (roll ambiguity) - that error cascades to all child bones and
    # shows up as a displaced mesh on export.
    for i, b in enumerate(arm_data.bones):
        if i < len(local_rest):
            lp, lq = local_rest[i]
            try:
                b["mu_rest_pos"] = (lp.x, lp.y, lp.z)
                b["mu_rest_quat"] = (lq.x, lq.y, lq.z, lq.w)
            except Exception:
                pass

    return arm_obj, bone_names, world


def _bind_transform_point(bind_world, node, pos):
    """Transform a point from bone-local space into model space using the
    bone's bind world matrix (identity fallback for invalid nodes)."""
    if bind_world is None or node < 0 or node >= len(bind_world):
        return pos
    m = bind_world[node]
    v = m @ Vector((pos[0], pos[1], pos[2], 1.0))
    return (v[0], v[1], v[2])


def _extract_mesh_arrays(mesh, bind_world=None):
    """Expand triangles into flat arrays + dedupe.

    BMD vertices/normals are stored in BONE-LOCAL space; we transform them into
    model space via the bind world matrix so the mesh aligns with the skeleton
    (same as the C# client's boneMatrix[node] * vertex).
    """
    pos_map = {}
    positions, normals, uvs, bones = [], [], [], []

    def corner(v_idx, n_idx, t_idx):
        if v_idx < 0 or v_idx >= len(mesh.vertices):
            return -1
        v = mesh.vertices[v_idx]
        n = mesh.normals[n_idx] if 0 <= n_idx < len(mesh.normals) else (v[1], (0, 1, 0), 0)
        t = mesh.tex_coords[t_idx] if 0 <= t_idx < len(mesh.tex_coords) else (0, 0)
        node = v[0]

        # position: full bind transform (rotation + translation)
        pos = _bind_transform_point(bind_world, node, v[1])
        # normal: bind rotation only
        if bind_world is not None and 0 <= node < len(bind_world):
            nm = bind_world[node].to_3x3() @ Vector(n[1])
        else:
            nm = Vector(n[1])

        key = (round(pos[0], 5), round(pos[1], 5), round(pos[2], 5),
               round(nm.x, 5), round(nm.y, 5), round(nm.z, 5),
               round(t[0], 6), round(t[1], 6), node)
        if key not in pos_map:
            pos_map[key] = len(positions)
            positions.append(pos)
            normals.append((nm.x, nm.y, nm.z))
            uvs.append(t)
            bones.append(node)
        return pos_map[key]

    faces = []
    for tri in mesh.triangles:
        vi, ni, ti = tri.vertex_index, tri.normal_index, tri.tex_coord_index
        i0 = corner(vi[0], ni[0], ti[0])
        i2 = corner(vi[2], ni[2], ti[2])
        i1 = corner(vi[1], ni[1], ti[1])
        if i0 < 0 or i1 < 0 or i2 < 0:
            continue
        faces.append((i0, i1, i2))  # BMD winding is CCW (0,1,2)
        if tri.polygon == 4:
            i3 = corner(vi[3], ni[3], ti[3])
            if i3 >= 0:
                faces.append((i0, i2, i3))
    return positions, normals, uvs, bones, faces


def _build_mesh(mesh: BMDTextureMesh, arm_obj, bone_names, index, name_base, scale,
                 flip_uv=True, use_vertex_normals=True, bind_world=None):
    """构建单个网格对象并绑定顶点组 + 骨架修改器。"""
    positions, normals, uvs, bones, faces = _extract_mesh_arrays(mesh, bind_world)

    me = bpy.data.meshes.new(f"{name_base}_mesh_{index}")
    bm = bmesh.new()
    for (x, y, z) in positions:
        bm.verts.new((x * scale, y * scale, z * scale))
    bm.verts.ensure_lookup_table()
    for f in faces:
        try:
            bm.faces.new([bm.verts[i] for i in f])
        except ValueError:
            pass  # 退化面
    bm.normal_update()
    if uvs:
        uv_layer = bm.loops.layers.uv.new("UVMap")
        for fi, f in enumerate(bm.faces):
            for li, loop in enumerate(f.loops):
                vi = faces[fi][li]
                loop[uv_layer].uv = (uvs[vi][0],
                                       (1.0 - uvs[vi][1]) if flip_uv else uvs[vi][1])
    bm.to_mesh(me)
    bm.free()

    # 法线
    if normals and use_vertex_normals:
        # Apply BMD stored normals for smooth shading (matches the game).
        try:
            me.use_auto_smooth = True
            me.normals_split_custom_set_from_vertices(
                [(n[0], n[1], n[2]) for n in normals])
        except Exception:
            pass
    if normals:
        me.attributes.new(name="mu_normals", type="FLOAT_VECTOR", domain="POINT")
        attr = me.attributes["mu_normals"]
        for i, n in enumerate(normals):
            attr.data[i].vector = n

    obj = bpy.data.objects.new(f"{name_base}_mesh_{index}", me)
    bpy.context.collection.objects.link(obj)

    # 顶点组(node → 骨骼)
    if arm_obj and bones:
        group_map = {}
        for i, b_idx in enumerate(bones):
            if b_idx < 0 or b_idx >= len(bone_names):
                continue
            g = group_map.get(b_idx)
            if g is None:
                g = obj.vertex_groups.new(name=bone_names[b_idx])
                group_map[b_idx] = g
            g.add([i], 1.0, "REPLACE")

        mod = obj.modifiers.new("Armature", "ARMATURE")
        mod.object = arm_obj
        print("[MuOnline] mesh %s: %d vertex groups / %d verts -> armature %s" % (
            obj.name, len(group_map), len(me.vertices), arm_obj.name))

    if not obj.data.materials:
        mat = bpy.data.materials.new(f"{name_base}_default_mat")
        mat.use_nodes = True
        obj.data.materials.append(mat)

    obj.muonline.is_mu_model = True
    obj.muonline.texture_path = mesh.texture_path
    return obj


# ---------------------------------------------------------------- 动作


def _build_actions(bmd: BMDData, arm_obj, bone_names, world, scale=1.0):
    """为每个动作创建相对绑定姿态的关键帧。返回 [ (action_name, frame_range) ]。"""
    if not bmd.actions or not arm_obj:
        return []

    action = bpy.data.armatures[arm_obj.data.name].animation_data
    if action is None:
        arm_obj.animation_data_create()
    adata = arm_obj.animation_data
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)
    bpy.ops.object.mode_set(mode="POSE")

    created = []
    best_clip = None
    best_keys = 0
    for a, act in enumerate(bmd.actions):
        keys = act.num_animation_keys
        if keys <= 1:
            continue
        clip = bpy.data.actions.new(f"action_{a}")
        created.append((clip.name, keys))
        if keys > best_keys:
            best_keys = keys
            best_clip = clip
        # fcurve_ensure_for_datablock requires the action to be the active
        # action of the armature, so temporarily assign it while building.
        adata.action = clip

        # 绑定姿态(本地,parent 空间)
        rest = {}
        for i, bone in enumerate(bmd.bones):
            if bone.is_dummy or not bone.matrixes or i >= len(bone_names):
                continue
            m0 = bone.matrixes[0]
            rp = m0.positions[0] if m0.positions else (0, 0, 0)
            rq = m0.quaternions[0] if m0.quaternions else (0, 0, 0, 1)
            rest[i] = (Vector(rp), Quaternion((rq[3], rq[0], rq[1], rq[2])))

        for i, bone in enumerate(bmd.bones):
            if bone.is_dummy or i >= len(bone_names):
                continue
            if a >= len(bone.matrixes):
                continue
            bm = bone.matrixes[a]
            if not bm.positions:
                continue
            pb = arm_obj.pose.bones.get(bone_names[i])
            if pb is None:
                continue
            pb.rotation_mode = "QUATERNION"

            rest_pos, rest_quat = rest.get(i, (Vector((0, 0, 0)), Quaternion()))

            # Create fcurves directly (much faster than pb.keyframe_insert:
            # no depsgraph update is triggered for every single keyframe).
            name = bone_names[i]
            loc_path = 'pose.bones["%s"].location' % name
            rot_path = 'pose.bones["%s"].rotation_quaternion' % name
            loc_fcs = [clip.fcurve_ensure_for_datablock(arm_obj, loc_path, index=j) for j in range(3)]
            rot_fcs = [clip.fcurve_ensure_for_datablock(arm_obj, rot_path, index=j) for j in range(4)]
            loc_pts = [fc.keyframe_points for fc in loc_fcs]
            rot_pts = [fc.keyframe_points for fc in rot_fcs]
            for k in range(keys):
                # lockPositions: root bone (index 0) keeps frame-0 position
                if act.lock_positions and i == 0 and bm.positions:
                    p = bm.positions[0]
                else:
                    p = bm.positions[k]
                q = bm.quaternions[k] if k < len(bm.quaternions) else rest_quat
                anim_quat = Quaternion((q[3], q[0], q[1], q[2]))
                # 相对绑定姿态的 delta
                delta_pos = rest_quat.inverted() @ (Vector(p) - rest_pos)
                delta_quat = rest_quat.inverted() @ anim_quat

                dp = delta_pos * scale
                for j in range(3):
                    loc_pts[j].insert(frame=k, value=dp[j])
                for j in range(4):
                    rot_pts[j].insert(frame=k, value=delta_quat[j])

            for fc in loc_fcs + rot_fcs:
                fc.update()

        # Store metadata as Blender custom properties (Action.user_data was
        # removed in Blender 4.x; custom props work across 3.x and 5.x).
        clip["muonline_action_index"] = a
        clip["muonline_num_keys"] = keys
        clip["muonline_lock_positions"] = int(act.lock_positions)

    # Assign the action with the most keyframes so motion is visible.
    if best_clip is not None:
        adata.action = best_clip
        bpy.context.scene.frame_start = 0
        bpy.context.scene.frame_end = max(
            bpy.context.scene.frame_end, best_keys - 1)
        bpy.context.scene.frame_set(0)  # force evaluation at frame 0
    act = adata.action if adata else None
    print("[MuOnline] actions imported: %s" % (created,))
    print("[MuOnline] active action: %s" % (act.name if act else None))
    # Leave a clean object-mode state; the action stays assigned.
    try:
        bpy.ops.object.mode_set(mode="OBJECT")
    except Exception:
        pass
    return created


# ---------------------------------------------------------------- 入口


def import_bmd(bmd: BMDData, *, name=None, scale=1.0, load_textures=False,
               texture_root=None, flip_normals=False, flip_uv=True,
               use_vertex_normals=True, bmd_dir=None, auto_fit=True,
               set_active=True):
    """把解析好的 BMDData 导入当前场景。

    返回 (arm_obj, mesh_objects)。
    """
    name = name or (bmd.name or "MUModel")

    # Compute bind world matrices once (used for the vertex-space transform).
    bind_world = []
    if bmd.bones:
        bind_world, _local = _world_bind_matrices(bmd)

    if auto_fit:
        max_dim = 0.0
        for m in bmd.meshes:
            for node, pos in m.vertices:
                p = _bind_transform_point(bind_world, node, pos)
                max_dim = max(max_dim, abs(p[0]), abs(p[1]), abs(p[2]))
        if max_dim > 0.0:
            scale = 2.0 / max_dim
            print("[MuOnline] auto-fit scale: %.4f (max dim %.1f)" % (scale, max_dim))
    arm_obj = None
    bone_names = []
    world = []

    if bmd.bones:
        arm_obj, bone_names, world = _build_armature(bmd, scale, name + "_Armature")

    mesh_objects = []
    for i, mesh in enumerate(bmd.meshes):
        obj = _build_mesh(mesh, arm_obj, bone_names, i, name, scale,
                          flip_uv=flip_uv, use_vertex_normals=use_vertex_normals,
                          bind_world=bind_world)
        if flip_normals:
            me = obj.data
            me.flip_normals()
        # Group meshes under the armature so animation/bones/mesh/texture all
        # live under a single skeleton root.
        if arm_obj is not None:
            obj.parent = arm_obj
        obj.muonline.import_scale = scale
        mesh_objects.append(obj)

    created_actions = []
    if arm_obj:
        created_actions = _build_actions(bmd, arm_obj, bone_names, world, scale)

    if load_textures:
        _attach_textures(bmd, mesh_objects, texture_root, bmd_dir=bmd_dir)

    # Leave the armature active + selected so its assigned action is
    # immediately visible in the Action Editor, and SPACE (play) works
    # right after import without needing to pick the skeleton manually.
    if arm_obj is not None:
        if set_active:
            bpy.context.view_layer.objects.active = arm_obj
            arm_obj.select_set(True)
            try:
                bpy.context.view_layer.update()
            except Exception:
                pass
        arm_obj.muonline.import_scale = scale
    print("[MuOnline] imported %s: meshes=%d bones=%d actions=%d" % (
        name, len(bmd.meshes), len(bmd.bones), len(bmd.actions)))
    if created_actions:
        print("[MuOnline] animation auto-assigned to %s - press SPACE to play, "
              "or open the Action Editor (skeleton is already selected)." % arm_obj.name)

    return arm_obj, mesh_objects, created_actions


def _attach_textures(bmd, mesh_objects, texture_root, bmd_dir=None):
    """Load OZJ/OZT/TGA textures for each mesh.

    BMD stores logical texture names with .jpg/.tga extensions while the real
    files are .ozj/.ozt, so we map extensions and search several roots.
    """
    from ..formats import textures as tex_mod
    import os

    roots = []
    if texture_root:
        roots.append(texture_root)
    if bmd_dir:
        roots.append(bmd_dir)
    if not roots:
        print("[MuOnline] no texture root; skipping textures")
        return

    # MU maps logical extensions to real files: .jpg/.bmp -> .ozj, .tga -> .ozt
    EXT_FALLBACK = {
        ".jpg": [".ozj"], ".jpeg": [".ozj"], ".bmp": [".ozj"], ".png": [".ozj"],
        ".tga": [".ozt"],
    }

    found = 0
    for obj in mesh_objects:
        rel = obj.muonline.texture_path
        if not rel:
            continue
        rel_clean = rel.replace("\\", "/").lstrip("/")
        base = os.path.basename(rel_clean)
        ext = os.path.splitext(base)[1].lower()

        candidates = [rel_clean, base]
        for fb in EXT_FALLBACK.get(ext, []):
            candidates.append(os.path.splitext(rel_clean)[0] + fb)
            candidates.append(os.path.splitext(base)[0] + fb)

        resolved = None
        for cand in candidates:
            for root in roots:
                p = os.path.join(root, cand)
                if os.path.exists(p):
                    resolved = p
                    break
            if resolved:
                break

        if not resolved:
            print("[MuOnline] texture not found: %s (roots: %s)" % (rel, roots))
            continue

        try:
            rext = os.path.splitext(resolved)[1].lower()
            with open(resolved, "rb") as f:
                img = tex_mod.decode_texture(f.read(), rext)
            # Name the image with the ORIGINAL logical BMD texture name
            # (e.g. "Tree_a.tga") so the jpg/tga family survives export:
            # the game loads stem.ozj for a .jpg/.png and stem.ozt for a
            # .tga, and we must re-encode to the matching format.
            logical_base = os.path.basename(rel_clean)
            if os.path.splitext(logical_base)[1].lower():
                img_name = logical_base
            else:
                img_name = os.path.splitext(os.path.basename(resolved))[0]
            # Load through a temp PNG so orientation matches Blender's own loader.
            import tempfile
            if img_name not in bpy.data.images:
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                img.convert("RGBA").save(tmp.name, format="PNG")
                tmp.close()
                bimg = bpy.data.images.load(tmp.name)
                bimg.pack()  # pack while the source file still exists
                bimg.name = img_name
                os.unlink(tmp.name)
            else:
                bimg = bpy.data.images[img_name]
                bimg.pack()
            mat = bpy.data.materials.new(img_name)
            mat.use_nodes = True
            nt = mat.node_tree
            nt.nodes.clear()
            bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
            out = nt.nodes.new("ShaderNodeOutputMaterial")
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = bimg
            nt.links.new(bsdf.inputs["Base Color"], tex.outputs["Color"])
            nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)
            found += 1
        except Exception as exc:
            print("[MuOnline] texture decode failed for %s: %s" % (resolved, exc))

    print("[MuOnline] textures attached: %d/%d" % (found, len(mesh_objects)))

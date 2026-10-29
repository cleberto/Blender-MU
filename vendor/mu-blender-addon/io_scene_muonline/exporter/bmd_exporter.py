# -*- coding: utf-8 -*-
"""BMD model export - serialize Blender meshes/armature/actions into BMDData -> bytes."""

import bpy
from mathutils import Vector, Quaternion, Matrix

from ..formats.bmd import (
    BMDData, BMDTextureBone, BMDTextureAction, BMDTextureMesh,
    BMDTriangle, BMDBoneMatrix, write_bmd,
)
from ..formats.binary import BinaryWriter  # noqa: F401


# ---------------------------------------------------------------- ??


def _topo_order(arm):
    """? armature.data.bones ?

     (order: [bone, ...], old_index_of_each_order) ?
    """
    bones = list(arm.data.bones)
    order = []
    visited = set()

    def visit(bone):
        if bone.name in visited:
            return
        visited.add(bone.name)
        if bone.parent:
            visit(bone.parent)
        order.append(bone)

    for bone in bones:
        visit(bone)
    return order


def _rest_local(bone, arm_space_index, scale=1.0):
    """? rest pose ? (position, quaternion)?"""
    # Prefer the exact original rest stored at import time (BMD units,
    # xyz / quat x,y,z,w). EditBone head/tail/roll cannot exactly reproduce
    # a ~180 deg rotation (roll ambiguity), which would displace children.
    if "mu_rest_pos" in bone and "mu_rest_quat" in bone:
        pos = bone["mu_rest_pos"]
        quat = bone["mu_rest_quat"]
        return (pos[0], pos[1], pos[2]), (quat[0], quat[1], quat[2], quat[3])
    local = bone.matrix_local.copy()
    if bone.parent:
        local = bone.parent.matrix_local.inverted() @ local
    pos = local.to_translation() / scale
    quat = local.to_quaternion()
    return (pos.x, pos.y, pos.z), (quat.x, quat.y, quat.z, quat.w)


def _collect_bones(arm_obj, scale=1.0):
    """ (bones_order, parent_indices, rest_local[(pos,quat)])?"""
    order = _topo_order(arm_obj)
    index_of = {b.name: i for i, b in enumerate(order)}
    parents = []
    rests = []
    for b in order:
        if b.parent and b.parent.name in index_of:
            parents.append(index_of[b.parent.name])
        else:
            parents.append(-1)
        rests.append(_rest_local(b, index_of[b.name], scale))
    return order, parents, rests


# ---------------------------------------------------------------- 网格


def _material_image_name(mat):
    """Return the logical BMD texture name for ONE material (dedup suffix
    stripped): "pk_mon04.jpg.001" -> "pk_mon04.jpg". '' if no TEX_IMAGE."""
    import os
    import re
    if getattr(mat, "node_tree", None) is None:
        return ""
    for node in mat.node_tree.nodes:
        if node.type == "TEX_IMAGE" and node.image is not None:
            base = os.path.basename(node.image.name)
            return re.sub(r"\.\d{3,}$", "", base)
    return ""


def _mesh_texture_name(obj, tex_name=""):
    """Resolve the BMD texture_path for a mesh object.

    Priority: explicit tex_name (UI) > stored muonline.texture_path
    (BMD-imported) > derived from the first material's TEX_IMAGE image.
    Returns '' when nothing is found.
    """
    if tex_name:
        return tex_name
    try:
        logical = getattr(getattr(obj, "muonline", None), "texture_path", "") or ""
    except Exception:
        logical = ""
    if logical:
        return logical
    mats = [m for m in obj.data.materials if m is not None]
    for mat in mats:
        n = _material_image_name(mat)
        if n:
            return n
    return ""


def _short_tex_stem(logical, max_stem=28):
    """Return a texture STEM safe for the BMD 32-byte texture_path field.

    BMD stores texture_path in a fixed 32-byte field and the game resolves the
    actual file via Path.ChangeExtension (stem.jpg -> stem.ozj).  The exported
    .ozj/.ozt on disk must use the SAME stem, otherwise long names (common on
    third-party / downloaded models) are truncated and the game cannot find the
    texture.  We cap the stem to `max_stem` bytes (so stem + .jpg/.tga <= 32 and
    stem + .ozj/.ozt <= 32), truncating the BASE not the extension so a unique
    short name is used consistently for both the BMD path and the written file.
    """
    import os
    import re
    base = os.path.basename(str(logical) or "")
    base = re.sub(r"\.\d{3,}$", "", base)  # strip Blender dedup suffix
    stem = os.path.splitext(base)[0]
    low = base.lower()
    ext = "ozt" if low.endswith((".tga", ".ozt")) else "ozj"
    if len(stem.encode("ascii", "replace")) > max_stem:
        stem = stem.encode("ascii", "replace")[:max_stem].decode("ascii")
    return stem, ext


def _texture_export_name(logical):
    """Map a logical BMD texture name to the DISK file name to write.

    Follows the import algorithm: the game stores .jpg/.jpeg/.bmp/.png in the
    BMD but loads the .ozj file, and .tga loads the .ozt file. So exporting a
    source image writes stem.ozj for jpg/jpeg/bmp/png and stem.ozt for tga.
    The stem is capped so it fits the 32-byte BMD texture_path exactly like it
    is written on disk (fixes missing textures on long third-party names).
    """
    stem, ext = _short_tex_stem(logical)
    return stem + "." + ext


def _texture_path_for_export(logical):
    """Return the BMD texture_path in the GAME convention.

    The game stores .jpg/.png in the BMD but loads the sibling .ozj,
    and .tga loads the sibling .ozt (TextureLoader does
    Path.ChangeExtension). So a texture exported as stem.ozj gets
    texture_path stem.jpg, one exported as stem.ozt gets stem.tga.
    The TS viewer matches by base name + compatible extension
    (jpg<->ozj, tga<->ozt), so it still finds the exported file.
    The stem is capped to the same value used when writing the .ozj/.ozt
    on disk, keeping the 32-byte BMD path consistent with the actual file.
    """
    stem, ext = _short_tex_stem(logical)
    return stem + (".tga" if ext == "ozt" else ".jpg")


def _mesh_to_bmd_mesh(obj, bone_index_of, scale, texture_path="",
                     bind_world=None, material_filter=None, vert_bind_xform=None):
    """? Blender ??? BMDTextureMesh?

    vert_bind_xform: optional 4x4 (identity if None) mapping the mesh's
        OBJECT-space vertices into the bind/bone space (where bind_world and
        bone.matrix_local live).  None keeps the historical behavior (mesh
        vertices taken as if already in armature space), used by BMD
        round-trip.  Generic (FBX/GLB) export passes the mesh's transform so
        non-identity meshes map correctly (fixes misposition/distortion).
    """
    me = obj.data
    # calc_normals_split was deprecated in Blender 4.1 and removed later;
    # Recompute split normals (loop.normal) across Blender 3.x/4.x/5.x.
    # calc_normals_split() and calc_normals() were removed in Blender 5.1,
    # so fall back to a bmesh recalc there.
    if hasattr(me, "calc_normals_split"):
        me.calc_normals_split()
    elif hasattr(me, "calc_normals"):
        me.calc_normals()
    else:
        import bmesh
        bm = bmesh.new()
        try:
            bm.from_mesh(me)
            bm.normal_update()
            if hasattr(bm, "calc_loop_normals"):
                bm.calc_loop_normals()
            bm.to_mesh(me)
        finally:
            bm.free()
    me.calc_loop_triangles()

    uv_layer = None
    for layer in me.uv_layers:
        uv_layer = layer
        break

    # ? ? ?
    vg_index = {}
    for g in obj.vertex_groups:
        if g.name in bone_index_of:
            vg_index[g.index] = bone_index_of[g.name]

    def node_of(vert):
        best = 0
        best_w = -1.0
        for g in obj.vertex_groups:
            try:
                w = g.weight(vert)
            except Exception:
                continue
            if w > best_w:
                best_w = w
                best = g.index
        return vg_index.get(best, 0)

    vertex_map = {}
    normal_map = {}
    uv_map = {}
    vertices = []
    normals = []
    tex_coords = []
    triangles = []

    # BMD stores mesh vertices/normals in BONE-LOCAL space. The Blender mesh
    # is in object space (bind-transformed, scaled by `scale`), so we map it
    # back to bone-local with the inverse bind matrix before writing.
    bind_inv = []
    if bind_world:
        for m in bind_world:
            bind_inv.append(m.inverted())

    def corner(vert_idx, loop):
        co = me.vertices[vert_idx].co / scale
        node = node_of(vert_idx)
        n = loop.normal
        if vert_bind_xform is not None:
            co = vert_bind_xform @ co
            n = vert_bind_xform.to_3x3() @ n
        if bind_inv and 0 <= node < len(bind_inv):
            m_inv = bind_inv[node]
            co = m_inv @ co
            n = m_inv.to_3x3() @ n
        u, v = 0.0, 0.0
        if uv_layer:
            u, v = uv_layer.data[loop.index].uv
            v = 1.0 - v  # Blender v=0 bottom -> BMD v=0 top

        vkey = (node, round(co.x, 5), round(co.y, 5), round(co.z, 5))
        if vkey not in vertex_map:
            vertex_map[vkey] = len(vertices)
            vertices.append((node, (co.x, co.y, co.z)))
        vi = vertex_map[vkey]

        nkey = (node, round(n.x, 5), round(n.y, 5), round(n.z, 5), vi)
        if nkey not in normal_map:
            normal_map[nkey] = len(normals)
            normals.append((node, (n.x, n.y, n.z), vi))
        ni = normal_map[nkey]

        ukey = (round(u, 6), round(v, 6))
        if ukey not in uv_map:
            uv_map[ukey] = len(tex_coords)
            tex_coords.append(ukey)
        ti = uv_map[ukey]
        return vi, ni, ti

    # Pre-triangulation (game correctness + correct texture mapping): every
    # polygon is split into polygon=3 triangles using Blender's OWN loop
    # triangulation (calc_loop_triangles).  This picks seam-aware diagonals
    # based on the real UV layout, so UVs stay aligned after triangulation.
    # (The MU map-object renderer mishandles polygon=4 quads, and a manually
    # fanned diagonal can cross a UV seam and misplace the texture - the same
    # way the working "import BMD -> re-export BMD" path produces triangles.)
    for tri in me.loop_triangles:
        if material_filter is not None and \
           tri.polygon_index < len(me.polygons) and \
           me.polygons[tri.polygon_index].material_index != material_filter:
            continue
        tris_corners = [corner(me.loops[li].vertex_index, me.loops[li])
                        for li in tri.loops]
        _emit_triangle(triangles, tris_corners, 3)

    if not triangles:
        return None

    # Normalize the texture path to the DISK name we write
    # (stem + .ozj/.ozt) so the TS viewer can match it: it only
    # recognizes ozj/ozt/tga/png/jpg/jpeg extensions, so e.g. a
    # source 'tex.bmp' / 'tex' (no extension) becomes 'tex.ozj'.
    _tp = texture_path or _mesh_texture_name(obj)
    if _tp:
        _tp = _texture_path_for_export(_tp)
    return BMDTextureMesh(
        texture=0,
        num_vertices=len(vertices),
        num_normals=len(normals),
        num_tex_coords=len(tex_coords),
        num_triangles=len(triangles),
        vertices=vertices,
        normals=normals,
        tex_coords=tex_coords,
        triangles=triangles,
        texture_path=_tp,
    )


def _mesh_to_bmd_meshes(obj, bone_index_of, scale, bind_world=None,
                        vert_bind_xform=None):
    """Return a LIST of BMDTextureMesh - one per material that has polygons.

    The BMD format binds exactly ONE texture per mesh, so a Blender mesh with
    several materials must be split into several BMD sub-meshes (this is how
    MU Online models carry multiple textures: multi-mesh + multi-texture).

    vert_bind_xform: forwarded to _mesh_to_bmd_mesh (see there).
    """
    mats = [m for m in obj.data.materials if m is not None]
    if not mats:
        return [_mesh_to_bmd_mesh(obj, bone_index_of, scale,
                                  bind_world=bind_world,
                                  vert_bind_xform=vert_bind_xform)]
    used = sorted({p.material_index for p in obj.data.polygons
                   if 0 <= p.material_index < len(obj.data.materials)})
    subs = []
    for mi in used:
        mat = obj.data.materials[mi]
        if mat is None:
            continue
        tp = _material_image_name(mat)
        sub = _mesh_to_bmd_mesh(obj, bone_index_of, scale, texture_path=tp,
                                bind_world=bind_world, material_filter=mi,
                                vert_bind_xform=vert_bind_xform)
        if sub is not None:
            subs.append(sub)
    if subs:
        return subs
    return [_mesh_to_bmd_mesh(obj, bone_index_of, scale,
                              bind_world=bind_world)]


def _emit_triangle(triangles, corners, poly_type):
    tris = []
    if poly_type == 3:
        tris = [corners[0], corners[1], corners[2]]
    elif poly_type == 4:
        tris = [corners[0], corners[1], corners[2], corners[3]]
    vi = [c[0] for c in tris]
    ni = [c[1] for c in tris]
    ti = [c[2] for c in tris]
    vi += [0] * (4 - len(vi))
    ni += [0] * (4 - len(ni))
    ti += [0] * (4 - len(ti))
    triangles.append(BMDTriangle(polygon=poly_type, vertex_index=vi,
                                 normal_index=ni, tex_coord_index=ti))


# ---------------------------------------------------------------- 动作


def _iter_action_fcurves(action):
    """Yield (data_path, array_index, fcurve) from an action.
    Handles both legacy (action.fcurves) and Blender 5.x layered actions."""
    if hasattr(action, "fcurves"):
        for fc in action.fcurves:
            yield fc.data_path, fc.array_index, fc
    else:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for fc in bag.fcurves:
                        yield fc.data_path, fc.array_index, fc


def _action_to_bone_matrices(action, order, rests, scale=1.0):
    """? Blender ?? BMDBoneMatrix ?"""
    fcurves = {b.name: {"loc": [None, None, None], "rot": [None, None, None, None]}
               for b in order}

    times = set()
    for data_path, arr_idx, fc in _iter_action_fcurves(action):
        if data_path.startswith('pose.bones["'):
            end = data_path.find('"]', len('pose.bones["'))
            bone_name = data_path[len('pose.bones["'):end]
            prop = data_path[end + 2:].lstrip(".")
            if bone_name not in fcurves:
                continue
            if prop == "location" and arr_idx < 3:
                fcurves[bone_name]["loc"][arr_idx] = fc
            elif prop == "rotation_quaternion" and arr_idx < 4:
                fcurves[bone_name]["rot"][arr_idx] = fc
            for kp in fc.keyframe_points:
                times.add(round(kp.co[0], 4))
    if not times:
        return None

    times = sorted(times)

    def eval_fc(fc, t):
        if fc is None:
            return 0.0
        return fc.evaluate(t)

    per_bone = {}
    for b in order:
        name = b.name
        rest_pos, rest_quat = rests[name]
        rq = Quaternion((rest_quat[3], rest_quat[0], rest_quat[1], rest_quat[2]))
        positions = []
        rotations = []
        for t in times:
            loc = Vector((eval_fc(fcurves[name]["loc"][0], t),
                          eval_fc(fcurves[name]["loc"][1], t),
                          eval_fc(fcurves[name]["loc"][2], t))) / scale
            # (?? rest)
            # rotation_quaternion RNA component order is (w, x, y, z), so
            # fcurve index 0 holds w, 1=x, 2=y, 3=z (the importer stores
            # delta_quat[j] at index j). Reading them as (x,y,z,w) would
            # shuffle the axis and rotate the animated mesh off the bones.
            q = Quaternion((
                eval_fc(fcurves[name]["rot"][0], t),
                eval_fc(fcurves[name]["rot"][1], t),
                eval_fc(fcurves[name]["rot"][2], t),
                eval_fc(fcurves[name]["rot"][3], t),
            ))
            q.normalize()
            # ?? = ?(??)  rest
            abs_q = rq @ q
            abs_pos = Vector(rest_pos) + rq @ loc
            positions.append((abs_pos.x, abs_pos.y, abs_pos.z))
            rotations.append(_quat_to_euler(abs_q))
        per_bone[name] = (positions, rotations)
    return times, per_bone


def _quat_to_euler(q):
    from ..formats.bmd import quaternion_to_bmd_angle
    return quaternion_to_bmd_angle((q.x, q.y, q.z, q.w))


# ---------------------------------------------------------------- 入口


def export_bmd(arm_obj, mesh_objs, *, name="export", version=12, scale=1.0,
               collect_all_actions=True, export_actions=True):
    """? Blender  BMDData?

    arm_obj:  (?? None ? ???/?)
    mesh_objs: (?)
    collect_all_actions: ? False ????(map ?
        ??? scan ??)
    export_actions: ? False ?? ???? action(bind ??)
        ???? ???? action 0 = bind, ????
     BMDData?
    """
    bmd = BMDData(version=version, name=name)

    # ---- ???
    if arm_obj:
        order, parents, rests = _collect_bones(arm_obj, scale)
        rest_by_name = {b.name: rests[i] for i, b in enumerate(order)}
        bone_index_of = {b.name: i for i, b in enumerate(order)}

        # action 0 = ?(1 ?)
        # World bind matrices (BMD units) for mapping mesh object-space coords
        # back to bone-local: matrix_local has translation scaled by `scale`.
        bind_world = []
        for b in order:
            m = b.matrix_local.copy()
            m.translation = m.translation / scale
            bind_world.append(m)

        bmd.actions = [BMDTextureAction(num_animation_keys=1, lock_positions=False)]
        for i, b in enumerate(order):
            pos, quat = rests[i]
            rq = Quaternion((quat[3], quat[0], quat[1], quat[2]))
            bmd.bones.append(BMDTextureBone(
                name=b.name, parent=parents[i], is_dummy=False,
                matrixes=[BMDBoneMatrix(
                    positions=[pos], rotations=[_quat_to_euler(rq)],
                    quaternions=[quat],
                )],
            ))

        # 其余动作
        # Collect ALL actions: the ones imported by the addon carry
        # 'muonline_action_index' (sorted by original order), plus any
        # user-created action or NLA strip. Only scanning the active
        # action + NLA lost every action but the best on multi-action BMDs.
        if export_actions:
            actions = []
            seen = set()
            adata = arm_obj.animation_data if arm_obj.animation_data else None
            if adata is not None:
                if adata.action is not None and adata.action.name not in seen:
                    actions.append(adata.action)
                    seen.add(adata.action.name)
                for track in adata.nla_tracks:
                    for strip in track.strips:
                        if strip.action is not None and strip.action.name not in seen:
                            actions.append(strip.action)
                            seen.add(strip.action.name)
                if collect_all_actions:
                    imported = sorted(
                        (a for a in bpy.data.actions if 'muonline_action_index' in a),
                        key=lambda a: a['muonline_action_index'])
                    for a in imported:
                        if a.name not in seen:
                            actions.append(a)
                            seen.add(a.name)
                    # Fallback for non-imported rigs (FBX/OBJ...): collect every action
                    # in the file whose fcurves actually drive THIS armature's bones,
                    # so animations are not lost just because they are not the active
                    # action or an NLA strip.
                    bone_set = {b.name for b in order}
                    for a in bpy.data.actions:
                        if a.name in seen:
                            continue
                        refs = 0
                        for data_path, _arr, _fc in _iter_action_fcurves(a):
                            if data_path.startswith('pose.bones["'):
                                end = data_path.find('"]', 12)
                                if data_path[12:end] in bone_set:
                                    refs += 1
                        if refs:
                            actions.append(a)
                            seen.add(a.name)

                for act in actions:
                    res = _action_to_bone_matrices(act, order, rest_by_name, scale)
                    if res is None:
                        continue
                    times, per_bone = res
                    nkeys = len(times)
                    # Preserve the original lock_positions flag (root keeps its
                    # frame-0 position) stored on the action at import time.
                    lock_pos = bool(act.get("muonline_lock_positions", False))
                    new_act = BMDTextureAction(num_animation_keys=nkeys,
                                                lock_positions=lock_pos)
                    if lock_pos:
                        # The lock_positions action header carries the root's
                        # position per keyframe; the game uses frame 0. The
                        # importer froze the root, so write its rest position.
                        root_pos = rests[0][0] if rests else (0.0, 0.0, 0.0)
                        new_act.positions = [tuple(root_pos)] * nkeys
                    bmd.actions.append(new_act)
                    idx = len(bmd.actions) - 1
                    for i, b in enumerate(order):
                        if b.name not in per_bone:
                            bmd.bones[i].matrixes.append(BMDBoneMatrix(
                                positions=[(0, 0, 0)] * nkeys,
                                rotations=[(0, 0, 0)] * nkeys,
                            ))
                            continue
                        positions, rotations = per_bone[b.name]
                        bmd.bones[i].matrixes.append(BMDBoneMatrix(
                            positions=positions, rotations=rotations,
                            quaternions=[(0, 0, 0, 1)] * nkeys,
                        ))
    else:
        bone_index_of = {}
        bind_world = []
        # Generic export without an armature still needs a
        # minimal 1-bone skeleton + a 1-key bind action: every mesh
        # vertex references bone 0 (node=0) and both the game and the
        # TS viewer expect that bone to exist (the viewer builds a
        # THREE.Skeleton from bmd.bones and reads bones[0].matrixWorld).
        bmd.actions = [BMDTextureAction(num_animation_keys=1,
                                        lock_positions=False)]
        bmd.bones.append(BMDTextureBone(
            name="Bone", parent=-1, is_dummy=False,
            matrixes=[BMDBoneMatrix(positions=[(0.0, 0.0, 0.0)],
                                    rotations=[(0.0, 0.0, 0.0)],
                                    quaternions=[(0.0, 0.0, 0.0, 1.0)])]))

    # ---- 网格
    for obj in mesh_objs:
        bmd.meshes.extend(_mesh_to_bmd_meshes(obj, bone_index_of, scale,
                                              bind_world=bind_world))

    return bmd


def export_bmd_bytes(arm_obj, mesh_objs, *, name="export", version=12, scale=1.0):
    bmd = export_bmd(arm_obj, mesh_objs, name=name, version=version, scale=scale)
    return write_bmd(bmd, version=version)


def _next_pow2(v):
    """Smallest power of two >= v (1, 2, 4, ..., 1024).  Returns v unchanged
    when v is already a power of two."""
    p = 1
    while p < v:
        p <<= 1
    return p


def export_mesh_textures(mesh_objs, tex_dir, max_size=0):
    """Encode each mesh material's image back to .ozj/.ozt in tex_dir.

    `max_size` > 0 downscales the exported image so its largest side is at
    most `max_size` pixels before encoding (helps reduce .ozj/.ozt file size
    for large textures). 0 disables downscaling.

    Two game-client constraints are always enforced:
      1. Every side must be <= 1024 (OZJReader/OZTReader throw "Invalid ...
         Dimensions" for any side > 1024, so such textures fail to load).
      2. Width and height must each be a power of two.  OZTReader pads the
         decoded image up to the next power of two (GetNearestPowerOfTwo), so
         non-power-of-two sizes (common on 3rd-party / downloaded models)
         render stretched / misaligned in-game.  Official MU BMD textures are
         already powers of two and are left byte-identical.
    """
    import os
    from ..formats import textures as tex_mod
    written = []
    seen = set()
    for obj in mesh_objs:
        mats = [m for m in (getattr(obj, 'data', None) or obj.data).materials if m is not None]
        for mat in mats:
            if mat.node_tree is None:
                continue
            img = None
            for node in mat.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image is not None:
                    img = node.image
                    break
            if img is None or img.name in seen:
                continue
            seen.add(img.name)
            try:
                if img.size[0] <= 0 or img.size[1] <= 0:
                    continue
                w, h = img.size
                px = [0.0] * (w * h * 4)
                img.pixels.foreach_get(px)  # bottom-up RGBA
                from PIL import Image
                pil = Image.new("RGBA", (w, h))
                pix = pil.load()
                for y in range(h):
                    for x in range(w):
                        i = ((h - 1 - y) * w + x) * 4
                        pix[x, y] = (int(px[i] * 255), int(px[i + 1] * 255),
                                     int(px[i + 2] * 255), int(px[i + 3] * 255))
                # MANDATORY client cap: the game's OZJReader/OZTReader reject any
                # texture wider or taller than 1024 (it throws "Invalid OZJ
                # Dimensions"), so such textures fail to load in-game (blank /
                # wrong texture) even though viewers/Blender read them fine.
                # We therefore ALWAYS downscale to <=1024 (LANCZOS). `max_size`
                # (if >0) forces an even smaller cap; 1024 is the hard ceiling.
                cap = max_size if (max_size and max_size > 0) else 1024
                if max(w, h) > cap:
                    ratio = cap / float(max(w, h))
                    nw = max(1, int(round(w * ratio)))
                    nh = max(1, int(round(h * ratio)))
                    pil = pil.resize((nw, nh), Image.LANCZOS)
                    w, h = nw, nh
                # Power-of-two constraint (see docstring): snap both sides up to
                # the next power of two (<=1024).  Already-power-of-two textures
                # (e.g. official MU BMD textures) are left byte-identical.
                nw = _next_pow2(w)
                nh = _next_pow2(h)
                if nw != w or nh != h:
                    pil = pil.resize((nw, nh), Image.LANCZOS)
                    w, h = nw, nh
                logical = img.name
                out_name = _texture_export_name(logical)
                # Some importers name the image without a .tga extension, so
                # also trust the source file format/path: TGA -> .ozt.
                if not out_name.lower().endswith(".ozt"):
                    src = (getattr(img, "filepath", "") or "").lower()
                    try:
                        fmt = img.file_format
                    except Exception:
                        fmt = ""
                    if src.endswith((".tga", ".ozt")) or fmt in ("TGA", "TARGA"):
                        out_name = os.path.splitext(out_name)[0] + ".ozt"
                if out_name.lower().endswith(".ozt"):
                    data = tex_mod.encode_ozt(pil)
                else:
                    data = tex_mod.encode_ozj(pil.convert("RGB"))
                out = os.path.join(tex_dir, out_name)
                with open(out, "wb") as f:
                    f.write(data)
                written.append(os.path.basename(out))
            except Exception as exc:
                print("[MuOnline] texture export failed for %s: %s" % (img.name, exc))
    return written

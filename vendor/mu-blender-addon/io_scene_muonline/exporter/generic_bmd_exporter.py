# -*- coding: utf-8 -*-
"""FBX / OBJ / GLB (generic) -> MU .bmd export - isolated from BMD round-trip.

WHY THIS FILE EXISTS (2026-08-25, user requirement):
  bmd_exporter.py is reserved for the BMD -> Blender -> BMD round-trip path.
  Generic rigs imported from FBX / OBJ / GLB bring their own coordinate
  conventions, skeleton layout and scaling, and any change made for those
  (e.g. world-orientation / axis-conversion handling) must NOT leak into the
  round-trip path.  So all generic-export *policy* lives here:
      * generic_scale multiplier semantics
      * which actions get embedded (all vs. bind-only for static)
      * future world-orientation / axis-correction handling
  The pure, format-level serializers (bone collection, mesh, action, texture)
  are imported from bmd_exporter and reused as-is.
"""

import bpy
from mathutils import Quaternion

from ..formats.bmd import (
    BMDData, BMDTextureBone, BMDTextureAction, BMDBoneMatrix, write_bmd,
)
from .bmd_exporter import (
    _collect_bones,
    _mesh_to_bmd_meshes,
    _iter_action_fcurves,
    _action_to_bone_matrices,
    _quat_to_euler,
    export_mesh_textures,
)


class _BakedMesh:
    """Lite view of an object exposing the fields _mesh_to_bmd_mesh needs, so a
    frame-0 evaluated (pose-deformed) mesh can be serialized as plain static
    geometry (no real object/armature link)."""

    def __init__(self, mesh, vertex_groups):
        self.data = mesh
        self.vertex_groups = vertex_groups


def _bake_static_meshes(obj, arm_obj, scale):
    """Bake `obj` at frame 0 (current deform pose) into a static BMD mesh list.

    The mesh is evaluated at frame 0 so the captured vertex positions are the
    exact frame-0 (first-pose / bind) geometry.  Serialization runs against a
    single identity bone (bind_world=[] -> vertices written as-is), so the game
    never re-deforms the mesh with a skeleton.  `vert_bind_xform` maps the
    baked object-space vertices into world-orientation model space.
    """
    scene = bpy.context.scene
    if scene.frame_current != 0:
        scene.frame_set(0)
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()

    ev = obj.evaluated_get(dg)
    me = ev.to_mesh(preserve_all_data_layers=True, depsgraph=dg)
    try:
        # mesh object space -> model space (world orientation):
        #   xform = (arm_world^-1 @ obj_world)  mesh rel. to armature
        #   world_rot = arm_world rotation      world direction
        if arm_obj is not None:
            xform = arm_obj.matrix_world.inverted() @ obj.matrix_world
            world_rot = arm_obj.matrix_world.to_3x3().normalized().to_4x4()
            mat = world_rot @ xform
        else:
            mat = obj.matrix_world
        wrapper = _BakedMesh(me, [])
        return _mesh_to_bmd_meshes(wrapper, {}, scale, bind_world=[],
                                   vert_bind_xform=mat)
    finally:
        ev.to_mesh_clear()


def export_generic_bmd(arm_obj, mesh_objs, *, name="export", version=12,
                       scale_multiplier=1.0, export_actions=True,
                       world_transform=None):
    """Serialize FBX/OBJ/GLB meshes (+ optional armature) into a BMDData.

    arm_obj: armature or None (static/unskinned export).
    mesh_objs: mesh objects to export.
    scale_multiplier: intuitive multiplier; exported BMD coords =
        Blender coords x this value (>1 enlarge, <1 shrink).  Mirrors
        export_bmd's inverse `scale` convention (it divides by `scale`).
    export_actions: True -> embed the armature's clip actions (animated
        export); False -> only the bind action (true static export).
    world_transform: optional root orientation Quaternion.  When None, the
        armature's own matrix_world rotation is baked into the root bone's
        rest so BOTH FBX & GLB export in world orientation (no source
        detection needed; FBX's ~identity world rotation leaves it unchanged).
        Kept here (and only here) so round-trip export is never affected.
    """
    scale = 1.0 / (scale_multiplier if scale_multiplier else 1.0)
    bmd = BMDData(version=version, name=name)

    # ---- STATIC export (no skeleton) -----------------------------------------
    # A static BMD must be the mesh baked at frame 0 (bind/first-pose geometry)
    # written against a single identity bone, so the game never re-deforms the
    # mesh with a skeleton (which is what caused "mesh distortion" when a
    # static rig was kept with real bones + bind offsets).  We therefore
    # evaluate each mesh at frame 0 and bake that deformed geometry directly.
    if not export_actions:
        bmd.actions = [BMDTextureAction(num_animation_keys=1,
                                        lock_positions=False)]
        bmd.bones.append(BMDTextureBone(
            name="Bone", parent=-1, is_dummy=False,
            matrixes=[BMDBoneMatrix(positions=[(0.0, 0.0, 0.0)],
                                    rotations=[(0.0, 0.0, 0.0)],
                                    quaternions=[(0.0, 0.0, 0.0, 1.0)])]))
        for obj in mesh_objs:
            bmd.meshes.extend(_bake_static_meshes(obj, arm_obj, scale))
        return bmd

    bind_world = []
    bone_index_of = {}
    if arm_obj:
        order, parents, rests = _collect_bones(arm_obj, scale)

        # ---- world orientation (uniform for FBX & GLB, no source detection) ----
        # glTF (GLB) imports with Y-up and leaves a -90 deg axis-correction as
        # the armature's matrix_world rotation; FBX imports are ~identity.  To
        # export BOTH in "world orientation" we bake the armature's world
        # ROTATION into the root bone's rest pose (rotation only - never the
        # translation, so position is preserved and static export stays exact).
        # Because mesh vertices are stored bone-local via bind_inv
        # (= matrix_local^-1) and the stored hierarchy rest now carries the
        # world rotation, the game's skinning yields W_rot @ co = the Blender
        # world orientation for both animated and static export.
        root_world_q = Quaternion((1.0, 0.0, 0.0, 0.0))
        if world_transform is not None:
            root_world_q = world_transform
        elif parents and parents[0] == -1:
            # bake armature world rotation (ignore translation/scale)
            root_world_q = arm_obj.matrix_world.to_3x3().normalized().to_quaternion()

        # world-oriented rest per bone: only the root(s) change - children keep
        # their relative rest (a global rotation does not affect relative pose).
        worlded_rests = list(rests)
        for i, par in enumerate(parents):
            if par == -1:
                pos, quat = rests[i]
                rq = Quaternion((quat[3], quat[0], quat[1], quat[2]))
                wq = root_world_q @ rq
                worlded_rests[i] = (pos, (wq.x, wq.y, wq.z, wq.w))

        rest_by_name = {b.name: worlded_rests[i] for i, b in enumerate(order)}
        bone_index_of = {b.name: i for i, b in enumerate(order)}

        bind_world = []
        for b in order:
            m = b.matrix_local.copy()
            m.translation = m.translation / scale
            bind_world.append(m)

        # action 0 = bind pose (1 key)
        bmd.actions = [BMDTextureAction(num_animation_keys=1,
                                        lock_positions=False)]
        for i, b in enumerate(order):
            pos, quat = worlded_rests[i]
            rq = Quaternion((quat[3], quat[0], quat[1], quat[2]))
            bmd.bones.append(BMDTextureBone(
                name=b.name, parent=parents[i], is_dummy=False,
                matrixes=[BMDBoneMatrix(
                    positions=[pos],
                    rotations=[_quat_to_euler(rq)],
                    quaternions=[quat],
                )],
            ))

        # extra clip actions (animated export only)
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
                # collect every action whose fcurves drive THIS armature (FBX/
                # GLB rigs have no 'muonline_action_index' marker, so scan all)
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
                    new_act = BMDTextureAction(num_animation_keys=nkeys,
                                               lock_positions=False)
                    bmd.actions.append(new_act)
                    for i, b in enumerate(order):
                        if b.name not in per_bone:
                            bmd.bones[i].matrixes.append(BMDBoneMatrix(
                                positions=[(0, 0, 0)] * nkeys,
                                rotations=[(0, 0, 0)] * nkeys,
                            ))
                            continue
                        ps, ro = per_bone[b.name]
                        bmd.bones[i].matrixes.append(BMDBoneMatrix(
                            positions=ps, rotations=ro,
                            quaternions=[(0, 0, 0, 1)] * nkeys,
                        ))
    else:
        # No armature: minimal 1-bone skeleton + bind action, as the game and
        # TS viewer expect bone 0 to exist.
        bmd.actions = [BMDTextureAction(num_animation_keys=1,
                                        lock_positions=False)]
        bmd.bones.append(BMDTextureBone(
            name="Bone", parent=-1, is_dummy=False,
            matrixes=[BMDBoneMatrix(positions=[(0.0, 0.0, 0.0)],
                                    rotations=[(0.0, 0.0, 0.0)],
                                    quaternions=[(0.0, 0.0, 0.0, 1.0)])]))

    for obj in mesh_objs:
        # Mesh object space -> armature (bind) space, so meshes under an
        # intermediate node with its own transform map correctly (fixes
        # static GLB misposition/distortion).  Identity when the mesh is a
        # plain child of the armature (common FBX case).
        xform = None
        if arm_obj is not None:
            xform = arm_obj.matrix_world.inverted() @ obj.matrix_world
        bmd.meshes.extend(_mesh_to_bmd_meshes(obj, bone_index_of, scale,
                                              bind_world=bind_world,
                                              vert_bind_xform=xform))
    return bmd


def export_generic_bmd_bytes(arm_obj, mesh_objs, *, name="export", version=12,
                             scale_multiplier=1.0, export_actions=True,
                             world_transform=None):
    bmd = export_generic_bmd(
        arm_obj, mesh_objs, name=name, version=version,
        scale_multiplier=scale_multiplier, export_actions=export_actions,
        world_transform=world_transform,
    )
    return write_bmd(bmd, version=version)

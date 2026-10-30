---
name: blender-mu-modernization
description: Blender-first modernization of MU Online monsters, NPCs, items and props in this repository. Use when importing BMD/GLB, resculpting, rebuilding topology, repairing facial symmetry, rigging jaws, baking PBR maps, validating animation or preparing GLB/review evidence. Especially required for Monster03/Budge Dragon mouth and face work.
---

# Blender MU modernization

Build reproducible candidates, not unsupported claims of “100%”. Preserve source assets and separate technical passes from human visual approval. This skill uses the tools actually present in this repository; do not invoke the inherited `tools/hdmodel` pipeline unless its files and host dependencies exist.

## 1. Load the minimum context

1. Read `AGENTS.md`, `docs/architecture.md` and `PIPELINE_STANDARDS.md`.
2. Run `py -3.9 tools/registry.py show <asset-id>`; read the selected version, `profiles/<asset>.json`, recipe and linked lessons.
3. For Monster03 also read `docs/dragon-v2-readiness.md`, `docs/monster03-v0002-experiments.md` and `knowledge/lessons/dragon-jaw-bone02.json`. Do not repeat rejected jaw cuts, global reweights, flat cheek patches or whole-head grafts.
4. Create a new run/output directory. Never overwrite source BMD, GLB, completed versions or another run.

## 2. Establish the baseline before editing

- Keep `00_ORIGINAL_BMD` and the received HD GLB immutable and in separate collections.
- Record source hashes, Blender version, mesh/LOD names, armature, actions, transforms, UVs, materials and existing defects.
- Render matched front, side, back, 3/4 and game-camera views. For animated assets, render every action at beginning/middle/end as an overview, then inspect every frame in motion.
- Reconcile the mesh with its own Armature Modifier. Never select “the last armature in the scene”.
- Do not apply object/armature scale or rotation to make a render look right. Record the measured conversion instead.

## 3. Work in this order

`source → reference → graybox topology → all-action deformation → symmetry/identity → UV/bake/materials → LODs → GLB round-trip → human review → target runtime`

Do not hide a geometry or rig failure with textures, lighting, subdivision, stronger normal maps or animation clamping. A beautiful still is not a deformation pass.

## 4. Mandatory mouth protocol

First classify the failure:

- **No jaw animation channel or no weights:** rig/import problem.
- **Jaw rotates but the surface stays closed:** missing mouth topology, not insufficient rotation.
- **Mouth opens but tears/crosses:** topology, hinge volume, weights and/or motion problem.

For a modern mouth, build separate, explicitly named surfaces as appropriate:

- `MOUTH_UPPER`: maxilla/upper lip; no lower-jaw weight.
- `MOUTH_LOWER`: mandible/lower lip; driven by the jaw bone.
- `MOUTH_CAVITY`, teeth, gums and tongue: internal geometry placed inside the closed envelope.
- Volumetric cheek/hinge tissue connecting the head to the jaw; no flat bands.

Create continuous upper/lower lip loops and a closed transition to the cranium/neck. Keep the inherited HD cranium/body when they are the approved visual baseline. A local head/neck rebuild needs compatible boundary rings; deleting a box of faces is not a graft.

Create `MOUTH_UPPER_RIM` and `MOUTH_LOWER_RIM` vertex groups for measurement. Use the original jaw island and joint pivot as spatial guides, not as production-density geometry. Never use global Automatic Weights after sculpting. Never “fix” crossing by clamping every jaw rotation without reviewing all actions.

For Monster03, `Bone02` already rotates and has influence; the inherited continuous head is the blocker. Rebuild the mouth locally instead of repeating attempts 01–05 or simply increasing rotation.

## 5. Mandatory facial-symmetry protocol

1. Measure in rest pose on a named region, normally vertices influenced by `Bip01 Head`; do not measure a posed frame.
2. Compare front and side renders with the original. Distinguish accidental asymmetry from intentional scars, horns, accessories, pose and UV/mirroring choices.
3. Correct only the affected region. Sculpt symmetry may be enabled for a region intended to be bilateral, but protect non-symmetric parts.
4. **Never run global `Mesh > Symmetrize` as a repair.** On a rigged/UV-mapped asset it can reverse the wrong side, change topology and desynchronize UVs, normals and weights.
5. If mirrored editing is used, verify pair correspondence, seam vertices, vertex groups/weights, UV islands, material assignment and normal seams afterward.
6. Exempt intentional asymmetry with `SYMMETRY_EXEMPT` and record the reason. Tolerance is relative to the region's size and expressed in mesh-local units, not assumed meters.

Symmetry is a diagnostic gate, not a demand to make every creature mathematically bilateral.

## 6. Run technical validation

From the repository root, with the candidate scene and real mouth objects:

```powershell
blender work/<asset>/candidate.blend -b --python-exit-code 1 `
  --python tools/validate_rig_symmetry.py -- `
  --profile profiles/<asset>.json `
  --report work/<asset>/rig-validation.json `
  --upper-mesh MOUTH_UPPER --lower-mesh MOUTH_LOWER
```

For the existing GLB before Blender editing:

```powershell
py -3.9 tools/inspect_glb_symmetry.py models/budge-dragon-hd.glb `
  --mesh LOD0 --bone "Bip01 Head" --output work/monster03/glb-symmetry.json
```

The Blender validator:

- checks a localized rest-pose symmetry region;
- verifies jaw influence and upper-jaw weight leakage;
- evaluates every integer frame of every action in the profile;
- checks finite deformation and upper/lower BVH collision;
- measures rim-opening range when rim groups exist;
- returns nonzero on failure or missing evidence.

It does not prove good anatomy, no tearing, attractive materials or runtime compatibility. Review side/front motion renders and the normal gameplay LOD, not only LOD0 close-ups.

## 7. Surface, LOD and export

Only after graybox motion passes:

- create/repair UVs and bake high-to-low normal/AO with appropriate cage and padding;
- use Base Color without duplicated baked lighting; Normal = tangent/Non-Color; ORM = AO/Roughness/Metallic;
- create LODs from the accepted topology and recheck mouth opening, wings, horns and silhouette at game distance;
- export GLB with only intended meshes/armature/actions/textures, using explicit action names/indices;
- reimport into a clean scene and repeat deformation checks.

Do not export studio helpers, hidden reference meshes or an Icosphere. Do not install into a client or overwrite a legacy prefab without separate authorization.

## 8. Evidence and completion

Each run must contain the candidate, validator JSON, all-action motion sheet/video, front/side symmetry comparison, LOD/game-camera comparison, effective parameters, hashes and remaining defects. Link the run in the asset version and record transferable lessons.

A candidate is only `eligible_for_review` after technical gates. `approved` requires all applicable human gates and, when in scope, target-runtime validation. If Blender or visual evidence is unavailable, report the work as unvalidated; never convert a missing test into a pass.

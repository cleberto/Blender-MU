# Model manifests (HD model pipeline)

One file per model: `<kind>/<asset>.yaml`. Monsters are the only supported kind (`monster/<asset>.yaml`, and
`kind: monster` in the file; any other kind is refused). `<asset>` is the generation asset id
(`monster14` = `Monster/Monster14.bmd`, the Elite Yeti pilot). It holds everything
monster-specific; the modules in `tools/hdmodellib/` read it through
`monsterspec.py` (`load`, `validate`, `names`). The current monster is
`HDMODEL_MONSTER` (default `monster14`); `tools/hdmodel monster <asset> …` sets it
for every stage it runs. The pilot's module constants (`gameready.GEO_ASSET`,
`face2.MOUTH`, `smooth.EXCLUDE_BONES`, …) are aliases computed from it.

Coordinates are MU model space in the generation pose: x towards the monster's
left, **-y the direction it faces**, z up. Pixels are those of the 1024 px head
close-up (`head-front-lit.png`).

`monster14.yaml` reproduces the pilot exactly (checked against the hard-coded
constants it replaced). Unset optional fields take the defaults in
`monsterspec.DEFAULTS`. Unknown keys and values of the wrong type are refused, naming the key
(`monsterspec.key_problems`).

## Fields

| Field | Req. | Meaning (pilot value) |
|---|---|---|
| `kind` | yes | the model kind; `monster` is the only supported one |
| `asset` | yes | id; must equal the file name (`monster14`) |
| `label` | | display name (`Elite Yeti`) |
| `bmd` | yes | Data-relative BMD (`Monster/Monster14.bmd`) |
| `texture_dirs` | | where its textures resolve (`[Monster]`) |
| `pose` | | generation pose `[action, key]` (`[0, 0]`, rest) |
| `budget` | | the original's triangle budget, recorded in shape metrics (12000) |
| `client.model` | yes | the client's `MODEL_*` name, written to `asset.extras.mu.model` (`MODEL_ELITE_YETI`) |
| `client.index` | | `MONSTER_MODEL_*` value (13) |
| `client.scale` | yes | CreateMonster `Object.Scale`; 1.0 when the client sets none (1.4) |
| `client.play_speed` | | per action, OpenMonsterModel (`[0.25, 0.2, 0.28, …]`) |
| `client.hold_last_actions` | | actions with `Loop` = hold the last key (`[6]`, DIE) |
| `bones.head` | if `head.enabled` | head bone first, then bones riding on it (`Bip01 Head`, `Box03`) |
| `bones.neck`, `bones.jaw`, `bones.feet` | | documentation and future use (`jaw: []`: the Yeti has none) |
| `bones.hands` | | texel density ×`budgets.density.hands` |
| `bones.sockets` | | bones the client attaches to; must survive (`Bip01 Head`, `Box03`) |
| `bones.limb_roots` | | limb separation in the LOD cut (Biped thighs and clavicles) |
| `bones.rigid` | | rigid accessories (weapons, wings) kept off smoothing; `[]` for the Yeti |
| `bones.spikes` | | `{bones, min_z}`: protrusions above `min_z` MU on these bones (shoulder crystals, 128) |
| `bones.smooth_exclude` | | bones the smoothing never touches (hands, fingers, claws Box06/07/11/12, feet, toes) |
| `bones.seam` | | `look-seams` close-up bones (right arm) |
| `concept.subject`, `concept.detail` | | Qwen prompt words of stage 2 |
| `concept.refine_prompt` | | stage 3 Qwen prompt (null: a generic one from `subject`) |
| `picks.concept` | MANUAL | the loved sheet, `<model>-<level>-s<seed>` (`qwen-faithful-s22`) |
| `picks.omni_seed` | MANUAL | the Omni point-control seed (2) |
| `picks.head_candidate` | MANUAL | the head clay-sheet pick (`omni-s2`) |
| `names.prefix` | | lineage prefix (`omni-faithful`; default `omni-<level>`) |
| `budgets.lod_triangles` | | LOD0–2 targets (`[8000, 2500, 1000]`) |
| `budgets.head_share`, `head_share_min` | | head triangle share (0.19) and its gate (0.17) |
| `budgets.density` | | texel density factors (head 2, hands 1.6, spikes 1.6) |
| `head.enabled` | | run stage 7 (false: no head bone, helmeted or small) |
| `depth.tile_mu_per_px` | | the concept's MU per px at 1536 (0.12) |
| `smoothing.passes`, `keep`, `dense`, `rebuild` | | the smoothing presets (`5a`, `5a2`; keep `5a2`) |
| `face.enabled` | | run stages 10–11 (false: no readable face) |
| `face.landmarks` | MANUAL | `name: [[concept x, y], [geometry x, y]]` read BY EYE (11 for the Yeti) |
| `face.mouth_group` | | landmarks `keep-mouth` moves rigidly with `nose_tip` |
| `face.region` | | close-up px box of the face (`[330, 560, 720, 860]`) |
| `face.plane_y_mu` | | face depth for the px → MU scale (-60) |
| `face.thin_part` | | `{thickness_mu, min_z, colour}`: thin parts that keep no face paint (crystals); null = none |
| `face.fit_mode` | | `keep-mouth` or `all` for the smooth2 fit |
| `face.passes` | MANUAL | ordered face-geometry passes (below) |
| `look.name`, `look.params` | | the look (`lookC2`: form 0.7, ao_power 2, lift 0.4, bleed) |
| `look.concept_light`, `look.paint` | | baked key direction; tooth, mouth, iris, pupil colours |
| `look.seam_compare` | | earlier looks shown by `look-seams` (`lookC`) |
| `lighting` | | per-model Enhanced lighting `{sky: 0..1, normalScale: 0..3}` written to `asset.extras.mu.lighting` (`{sky: 0.35, normalScale: 1.8}`); absent = the GLB carries none |
| `meshes` | | `[{index, texture, role, name?, size?, bone?}]`: the BMD meshes and their part roles (unlisted meshes are `body`). `body` = HD route (RGB, opaque; several body meshes need nothing: Omni makes one shape and xatlas one atlas). `card` = **legacy fallback** (operator 2026-10-15: "a model should contain all see-through components, rags, whatever, instead of old school hacks"; new monsters use generated parts) alpha card: the original geometry and one-bone skinning kept, RGB re-projected from the refined concept, the original alpha upscaled to `size` px (longest side, default 256), exported by every `write_variant` as an extra RGBA primitive in every LOD with `extras.mu {role, name}` (`hdmodellib/cards.py`; checked by `check_conventions(expect_cards)` and the gates `cards-present`, `card-alpha-iou`). Cards are framed with the body in `refs` (lit views include them; flat views and `rig.glb` stay body-only for Omni and the IoU gates; `<view>-cardmask.png` marks them). `effect` (additive glow, needs client work) and `accessory` (rigid per-bone part) are future. **`generated: true`** (with `role: body` and a `name`) marks a **generated part**: an original alpha mesh that Omni builds as solid geometry and that is kept (the Dragon's wings, operator 2026-10-15). It is body for Omni, the refs and the IoU (the original silhouettes include it), gets no card primitive (`cards-present` expects none in every LOD) and is coloured in the one RGB body atlas; its region of the generated surface (nearest original surface = the part mesh, or a bone of the part's limbs) takes the part's bones in both skin candidates (`gameready.part_skin`, labels diffused over `PART_RADIUS` 15 % of the diagonal), so the wings follow UpperArm/Forearm instead of the torso. Per part: `skin_limbs: true` also counts surface nearest a bone of the part's limbs (the Dragon's wing spars sit on the body mesh's forearms), `skin_radius` (fraction of the diagonal, default 0.15: Dragon wings and Wolf mane/straps both skin best there; 0.06 tore the Wolf, skin gate FAIL). Monsters without generated parts are unchanged. Open item: a generated part that needs real transparency would need alpha in its own material/primitive (not built; client support needed) |
| `bones.wings`, `bones.tail` | | extra bone groups (recorded for the Dragon; free-form lists are allowed and checked against the BMD by the tests) |
| `stages.<stage>` | | overrides: `skip: true`, `seeds: [...]` (shape, head), `verdict` (ingame), `note: …` |

## Face passes and generic operations

A pass edits the signed distance field of its `input` shape (`smooth2` or an
earlier pass) inside `box` (`[[x0,y0,z0],[x1,y1,z1]]` MU) at 0.25 MU, then the
driver rebuilds and fits it. `report` names its JSON (pilot: `face2/geometry.json`).
`ao_soft: {keep, regions: [{centre, radius}]}` keeps only `keep` of the AO
darkening inside the spheres. Ops run in order:

| `op` | Fields | Effect |
|---|---|---|
| `move-part` | `select {thin_below_mu, min_faces, front_y_below, below_z, centre_x, off_centre_mu, sides}`, `moves {side: [dx,dy,dz]}`, `reach_mu`, `grow_mu`, `eyes`, `eye_radius`, `landmarks {side: name}`, `landmark_plane` | thin parts selected by thickness and position are cut out of the field and moved rigidly (crystal plates off the eyes). First op of a pass only. |
| `carve-ellipsoid` | `centre`, `semi`, optional `surface_y`, `landmarks [left, right]` | `F = max(F, -E)`: a cavity (mouth); the landmarks move to its corners on `surface_y` |
| `add-ellipsoid` | `centre`, `semi`, `role` (`eyeball`, `filler`), `side`, optional `landmark` | `F = min(F, E)`: eyeballs, socket fillers; an eyeball's landmark moves to its front |
| `add-round-cone` | `top`, `tip`, `r_top`, `r_tip`, optional `landmark` | `F = min(F, C)`: fangs, horns; the landmark moves to the tip |

`role` (`mouth`, `fang`, `eyeball`, `filler`, `plate`) tells the look pass what to
paint: teeth on fangs and in the mouth, the dark mouth, iris and pupil on eyeball
fronts.

## Adding a monster

1. Copy `monster14.yaml` to `<asset>.yaml`; set `asset`, `label`, `bmd`, `client.*`
   (from `ZzzCharacter.cpp` CreateMonster and `ZzzOpenData.cpp` OpenMonsterModel).
2. Fill `bones.*` from the BMD's bone names (`python3 -c` with `mudata.load_bmd`); no
   head bone → `head.enabled: false`, `bones.head: []`.
3. Write `concept.subject/detail`; empty `picks`, `face.passes: []`, and
   `face.enabled: false` until the face is judged readable.
Second lineages: `tools/hdmodel monster <asset> run --root <new root> --reuse-from <root> --pick head_candidate=omni-s3`
(`HDMODEL_PICKS` carries the override to the child steps; the root's state remembers it).

Stage 4 shape source (`shape:`, `tools/hdmodellib/shapesource.py`): `generator: omni|trellis2`, `view:
front|left|back|right` (absent = Omni on the front view with the BMD point control, unchanged). Omni on another
view gets the point control turned to that view; TRELLIS.2's output is turned by the quarter turn that matches the
original best and refit to it. `repair: {voxel, close, foot_radius}` makes the dense mesh one closed manifold
(OpenVDB level set + closing) so direct decimation is accepted; `trim_ground` (fraction of the height) cuts a
generated ground slab away from the original's feet. `budgets.lod_max_genus` allows more LOD handles than the
default 8. `stages.smooth.skip: true`: the look starts from the depth variant. `gates.decisions:
{"<stage>/<gate id>": "<operator decision>"}` reports a FAIL as OPERATOR (kept, does not stop the driver); the
Wolf: the BMD silhouette gates after the operator's reimagined shape pick.

Stage folders: the pilot (monster14) keeps `head/`, `depth/`, `smooth*/`, `facefit/`, `face*/`, `look/` at the
concept root; every other monster writes them under `<root>/<asset>/` (`Names.dir`), so monsters can share a
`--root`. `review/` (gap metrics keyed by variant), `gameready/`, `paint21/`, `ingame/` stay shared and are keyed by
variant names: run two monsters of one root one after the other, not at once (`review/gap/metrics.json` is
read-modify-write).

4. `tools/hdmodel monster <asset> status`, then `run`: it stops at each MANUAL field.

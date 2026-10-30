# MU Asset Lab — Claude entry point

For any Blender modernization, follow `agent/blender-mu-modernization/SKILL.md` before editing geometry, rig, textures or exports. Read `AGENTS.md` for repository rules and `docs/architecture.md` for the registry.

Load only the relevant asset context with `py -3.9 tools/registry.py show <asset-id>`, then read its selected version, profile, recipe and lessons. Record every experiment and validate registry edits before finishing.

For Budge Dragon/Monster03, also read `docs/dragon-v2-readiness.md`, `docs/monster03-v0002-experiments.md` and `knowledge/lessons/dragon-jaw-bone02.json`. Blender validation comes first by user choice; Unity/OpenMU is the later target. The received GLB is an unapproved visual baseline. `Bone02` already animates: the production blocker is mouth/hinge topology, not lack of rotation. Do not repeat jaw cuts, global reweights, flat cheek patches, whole-head grafts or global Symmetrize.

The reusable build prototype and its limits are in `docs/monster-engine.md`; Monster03's profile is `profiles/monster03.json`. Use `tools/validate_rig_symmetry.py` with real upper/lower mouth objects and rim groups. Every declared action must be evaluated at every frame. A technical pass is only eligibility for human review, never final approval.



O próximo passo do Claude é executar a skill no Blender, construir MOUTH_UPPER, MOUTH_LOWER, cavidade e charneira volumétrica, corrigir a face regionalmente e anexar os testes visuais em movimento antes de qualquer aprovação.

# MU Asset Lab

Goal: rebuild and modernize MU assets with reproducible, reviewable evidence. Scope includes monsters, items, props, maps, effects, materials, shaders and animation.

For the reusable monster build command and per-asset profiles, read `docs/monster-engine.md` and `profiles/<monster>.json`. A one-command run creates a candidate and audits it; it never implies artistic or in-game approval. Keep monster-specific fixes in their profile/builder until validated across assets.

Start with `docs/architecture.md`. For Monster03, read `docs/dragon-v2-readiness.md`, `docs/monster03-v0002-experiments.md` and `docs/monster03-360-calibration.md` before editing: Unity/OpenMU is the eventual target, Blender-only validation is the current user preference, and the inherited GLB is the **visual baseline** for v0002 but not an approved final asset. Jaw splits plus two head/neck grafts have known failures. The parametric head is a mechanical study only; preserve the inherited HD cranium/body and retopologize the mouth locally. The board at `work/monster03/concepts/budge-head-realism-study01.png` is 2D guidance, not geometry. For a specific asset, run `py -3.9 tools/registry.py show <asset-id>` and read only the returned record, its selected version, recipe and relevant lessons. The large documents in `docs/hd-model-*.md` are inherited reference material; load only relevant sections.

Before creating or changing an asset, check `py -3.9 tools/registry.py list` for an existing identity. Give each attempt a new run record. A materially changed deliverable gets a new version; never overwrite a completed version's artifact. Record effective parameters, tool versions, exact input/output paths and SHA-256, steps, decisions, defects and validation evidence. Mark unknown values `null` or `unknown`; do not invent them.

Keep original game files and supplied reference models immutable. Use project-relative paths in records. Keep historical failures and rejected variants: they prevent repeated mistakes. A version is `approved` only after its defined quality gates and human visual review pass; a historical acceptance from another pipeline is evidence, not approval here.

Validate registry edits with `py -3.9 tools/registry.py validate`. Do not install into the game client or publish assets while merely cataloging or experimenting. Record lessons that apply beyond one run under `knowledge/lessons/`, with links to supporting runs or artifacts.

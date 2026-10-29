---
name: hd-model-pipeline
description: Run, re-run, check, extend or install from the HD model pipeline (tools/hdmodel monster) that turns a MU BMD monster into a game-ready HD GLB and installs an accepted one into the private client. Monsters are the only supported model kind. Use for "make an HD version of monster X", "re-run the Yeti / Dragon / Wolf", "add a new monster to the HD pipeline", "hdmodel doctor", "monster status", "MANUAL stop", "gate FAIL", "gates.decisions", "install the HD monster", "spin video", "in-game check of an HD GLB".
disable-model-invocation: true
---

# HD model pipeline (shared procedure)

This tier-1 workflow needs only file and shell tools. The procedure, with every command, is
`docs/hd-model-reproduce.md`. The reference (stages, gates, thresholds, dead ends) is
`docs/hd-model-pipeline.md`. The manifest schema is `tools/hdmodellib/manifests/README.md`.
Read the reproduce guide's sections 0–3 before you run anything, section 4 before an in-game
check or an install, and section 5 before you add a monster.

**Monsters are the only supported model kind.** Every manifest says `kind: monster` and lives
in `tools/hdmodellib/manifests/monster/`; players, NPCs and items are later changes.

## When to use

- Re-running or checking one of the three monsters: Elite Yeti `monster14`, Budge Dragon
  `monster03`, Bloody Wolf `monster44`.
- Adding a monster: a new `tools/hdmodellib/manifests/monster/<asset>.yaml` and its driver run.
- Installing an accepted GLB into the private client (`tools/hdmodel monster <asset> install`).
- Checking the host (`tools/hdmodel doctor`), reading a driver state or a gate report, making
  the old-vs-new video, preparing the in-game hand-off.

Not for client or server code changes; the in-game check *uses* the client but changes nothing
in it, and `install` only writes game data.

## Where it runs

- Any workspace with `tools/hdmodel` (mainline or a slot). Run `tools/slot status` first and
  stay inside the bound job (AGENTS.md session start rule). Long generation belongs in a slot.
- `install` needs a workspace whose client tree is the private clone `client/mumain-mutilate`
  (mainline, an idle slot or a `feature` job). It refuses a `pr`/`branch` job's public fork
  `client/mumain-sven` and any other tree. Never wire models into the public fork or an
  upstream pull request; publishing models needs the operator's separate approval.
- Never commit `.review/` (derived Webzen art). Commit with explicit paths, never `-a`. Never
  push without the operator's approval.

## Procedure

1. **Environment.**
   ```sh
   WS=$PWD && tools/slot status                                   # from the workspace root
   export HDMODEL_DATA=$PWD/client/mumain-mutilate/src/bin/Data
   S=$HOME/projects/mutilate-5/.review/hd-concept                 # the spike root: recorded runs (host-specific)
   ```
   The GPU lock is `$XDG_RUNTIME_DIR/mutilate/gpu.lock` (`HDMODEL_GPU_LOCK` overrides); the tool
   hands it to the generator wrappers itself. While spike tools may still run, use one lock for
   both (reproduce guide §1.7).
2. **Host check.** Run `tools/hdmodel doctor` (add `--json` for machine-readable output,
   `--full` to hash the weights).
   - Exit 1 means a prerequisite is missing; each FAIL names the document to follow. Fix it
     (reproduce guide §1, with the operator's approval for host installs) or report it; do not
     start GPU stages. Read-only work (`status`, `gates`, tests) may continue.
   - A `WARN` about the GPU lock means another job runs: wait **before GPU work**. Read-only
     work does not wait. The full action table is reproduce guide §1.8.
3. **State.** Run `tools/hdmodel monster <asset> status --root <root>`. Every attempt gets its
   own root under `.review/hd-models/`:
   - re-runs: `R=$(mktemp -d $WS/.review/hd-models/repro/<asset>-XXXX)` (after `mkdir -p`);
   - new monsters: `.review/hd-models/<name>`.

   `status` on a recorded root (`$S`, `$S/monsters/run`, `$S/monsters/wolf-t2`) is fine. Never
   pass a recorded root to `run` (use it as `--reuse-from` only) and never `--force` on it. A
   resumed attempt keeps its root.
4. **Run.**
   ```sh
   tools/hdmodel monster <asset> run --root <root> [--from S] [--to S] [--reuse-from <recorded root>]
   ```
   - Start long runs in the background with a log.
   - Poll in waits of 60 s or less, each with a done check: the log ends in
     `monster <asset>: stages … done`, `MANUAL stop at …` or `FAIL at …`.
   - Exit 0 means done, 2 a MANUAL stop, 1 a FAIL.
   - One step can be rerun alone: `tools/hdmodel step <command> …` (`step --help` lists them).
5. **At a MANUAL stop (exit 2).**
   - Report what the driver printed: the review files and the manifest field.
   - **Stop and ask the operator.** Never pick a concept, seed, head, landmarks or in-game
     verdict yourself. Never fill those fields from your own judgement, even when one option
     looks clearly better; you may describe the options.
   - After the operator answers, write the value they gave into the manifest, then `run` again.
6. **At a FAIL (exit 1).**
   - Read `<root>/<asset>/driver-logs/<stage>-gates.json`, or
     `HDMODEL_OUT=<root> tools/hdmodel gates <variant> --asset <asset>`.
     A FAIL is a stop. Fix the cause (reproduce guide §5.4, §6) or ask the operator.
   - Only the operator's decision may go into `gates.decisions`, and it must be quoted with its
     date: `"<stage>/<gate>": "operator <date>: <words>"`. Never add a decision on your own,
     and never change a threshold to make a gate pass. Never pass a FAIL with `--from`
     instead: record the decision, then run again. A decided FAIL stays FAIL in the report,
     with `OPERATOR DECISION: …` next to it.
7. **In-game check and verdict.**
   - The game copy is `<root>/ingame/<variant>-2048.glb` (maps capped at the client's 2048
     limit); `gates` runs `tools/mumodels check` on it (`game-copy-check`).
   - The in-game round (reproduce guide §4.1, helpers `tools/hdmodellib/ingame/`) tests it
     through an overlay; prove the GLB is drawn with the "is drawn from" log line. Its verdict
     is the operator's and goes into `stages.ingame.verdict`.
   - Optionally make the video:
     `HDMODEL_MONSTER=<asset> tools/hdmodel spin-video --hd <glb> --out <mp4>`.
8. **Install (only with a recorded verdict, only into the private client).**
   ```sh
   tools/hdmodel monster <asset> install [--glb <the accepted GLB>]
   git -C client/mumain-mutilate status --short       # the GLB and Models/ModelFiles.json only
   ```
   - It refuses, writing nothing: a client tree other than `client/mumain-mutilate`, no
     verdict, a GLB that `tools/mumodels check` refuses, a GLB naming another `MODEL_*`, maps
     above 2048. It records `stages.install` (source, sha256, date) and commits nothing.
   - Then the in-game check of installed data, `MU_DATA_OVERLAY` unset (reproduce guide §4.2):
     a client built from this tree logs `Model <MODEL_…> is drawn from …/Data/Monster/…glb`.
   - Commit the two data paths in the private clone with explicit paths, then move the
     superproject pin with a message that says why. Push only with the operator's go.

## Rules

- **The GPU lock.** One GPU job at a time, through one lock file. The ComfyUI commands,
  `spin-video` and the `gpu-run.sh` wrappers (started by the tool) take it themselves.
  - Never wrap them in another `flock`.
  - Never start a GPU job beside a running one.
  - Never kill another session's job. Kill only by explicit PID, and only your own.
- **ComfyUI's network namespace.**
  - On the pilot host ComfyUI runs in netns `vpn3`, and agent shells are in `vpn2`.
    `tools/hdmodel` re-runs ComfyUI commands in ComfyUI's namespace itself, through
    `tools/hdmodellib/incomfy.sh` and passwordless `sudo -n nsenter`.
  - For anything else, use `tools/hdmodellib/incomfy.sh <cmd>`.
  - If no ComfyUI process exists, ask the operator to start it (`sudo systemctl start comfyui`
    is a host-level action).
- **Build and resource rules** (AGENTS.md):
  - The pipeline itself builds nothing. A client build for the in-game check uses
    `CMAKE_BUILD_PARALLEL_LEVEL=8`, one build at a time; check `free -g` first.
  - No `dotnet` builds are part of this workflow; if one is needed, follow AGENTS.md's .NET
    limits.
  - No game client may run during generation.
  - Quit clients when done (`tools/muctl --client <name> quit`), and `tools/dev down`.
- **Outputs.** Never overwrite **recorded** outputs or GLBs (the three monsters' roots, the
  spike root). Write new files, a new root, or `/tmp`. Inside your own attempt root, a resumed
  or `--from` run rewrites later steps' outputs: that is expected there.
- **Scope.** Do not change gate thresholds without new evidence (`gates.py` `THRESHOLDS`
  records the evidence for each).

## Verification

Claims rest on command outcomes:

- `tools/hdmodel doctor` exit 0;
- the unit tests: `python3 -m unittest discover tests/hdmodel`, with `HDMODEL_DATA` exported,
  exit 0;
- `HDMODEL_OUT=<root> tools/hdmodel gates <variant> --asset <asset>`: exit 0 (no FAIL without
  a quoted operator decision), every MISSING explained (skipped stage, unmeasured pre-look
  colour, pilot-only review: reproduce guide §3.5);
- `tools/mumodels check` on the game copy (or the installed file), exit 0;
- after install: the installed file's sha256 equals `stages.install.sha256`, and in game
  `MuError.log` shows `Model <MODEL_…> is drawn from …` with no overlay.

AI stages are not bit-reproducible. Compare gates, silhouette IoU and review sheets (reproduce
guide §3.1), not file hashes. Deterministic post-steps (`glb-move-joints`, the game copy) must
reproduce their recorded sha256.

## Pitfalls

- **Recorded picks name new files after a from-scratch re-run.** Every AI stage regenerates,
  so a pick that is already set (`qwen-faithful-s22`) now points at a new image. Have the
  operator re-review, or empty the pick so the driver stops.
- **Omni on the front view loses forward parts of a quadruped.** The Wolf's four blades became
  one tusk. Use the side view (`shape: {generator: trellis2, view: left}`).
- **Phantom paint.** Concept parts in front of the body get painted onto it. Use
  `colour.part_masks`.
- **A TRELLIS.2 shape needs `shape.repair`.** `close: 2.5` is needed; 0.6 left a hollow rib
  cage.
- **Concept views larger than the shape** need `colour.register_views: true`.
- **No alpha cards for new monsters.** Use generated parts (`role: body, generated: true`).
  Real transparency in generated parts is not built.
- **A copied manifest carries the other monster's decisions.** Clear picks, `gates.decisions`,
  `stages` (verdict, install), `shape`, `colour`, look and lighting (reproduce guide §5.2
  step 5).
- **Unknown manifest keys are refused**, naming the key; a typo stops the run before any stage.
- **A shared BMD with `HiddenMesh`** (the Hound and the Hell Hound) renders both meshes; the
  manifest cannot drop one. Ask the operator before the concept.
- **`refs` uses the GPU briefly without the lock** (Eevee). Run it when `doctor` shows the lock
  free.
- **Refs use the original texture.** The spike's Yeti refs used an upscaled texture, so a fresh
  Yeti concept differs from the pilot's; a `--reuse-from` regression is unaffected.
- **A worker that died** (for example on API 429) leaves the driver state intact. Run
  `status`, then `run` again with the same `--root`.

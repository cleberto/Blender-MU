# HD model pipeline: reproduce it from scratch

This is the **procedure**: set up a host, re-run the three monsters, install an accepted one
into the private client, add a new one. **Monsters are the only supported model kind.** Every
command can be copied. The **reference** (what each stage does, every gate and threshold with
its evidence, the dead ends, the preview calibration) is
[`docs/hd-model-pipeline.md`](hd-model-pipeline.md); this guide links into it instead of
repeating it. AI agents: follow the skill
[`.agents/skills/hd-model-pipeline/SKILL.md`](../.agents/skills/hd-model-pipeline/SKILL.md),
which points back here.

Status: mainline tool `tools/hdmodel` (OpenSpec change `add-hd-model-pipeline`, capability
`hd-model-pipeline`). History: it was built in spike 3 (`spike-hd-guided-geometry`) as
`tools/hdspike` on the spike branch `hd-geometry-spike`. The three monsters' recorded runs live in
that spike's output root (slot 5's `.review/hd-concept/`, the **spike root**; the evidence copies
are in mainline's `data/media/hd-guided-spike/`). New runs write `.review/hd-models/`.

Contents: [0 What you get](#0-what-you-get) · [1 Host](#1-host-prerequisites) ·
[2 Repository](#2-repository-side) · [3 Re-run the three monsters](#3-re-run-the-three-monsters) ·
[4 In-game check](#4-the-in-game-check) · [5 A new monster](#5-add-a-new-monster) ·
[6 Troubleshooting](#6-troubleshooting) · [7 Known gaps](#7-known-gaps)

Conventions in this guide:

- `$WS` is the workspace: mainline, or a slot bound to a `feature` job (its client tree is the
  private clone `client/mumain-mutilate`, which `install` needs). Set it once per shell, then
  check it:

  ```sh
  WS=$HOME/projects/mutilate-N      # a slot (or $HOME/projects/mutilate for mainline)
  cd "$WS" && tools/slot status     # mainline, or a feature job; a pr/branch job cannot install
  ```

  Every command runs from `$WS` unless it says otherwise. Install blocks run in a subshell
  `( … )`, so they leave the shell in `$WS`.
- **Host-specific** marks a value of the pilot host (user `jev`, the `vpn3` network namespace,
  paths under `~/ai`). Each one comes with its generic equivalent.
- **MANUAL** marks a stop where the operator decides. Never decide for the operator.
- "Gate" means a check `tools/hdmodel gates` evaluates after a stage
  ([reference](hd-model-pipeline.md#gates-in-one-command)).

## 0 What you get

One command per monster, `tools/hdmodel monster <asset> run`, turns the original MU BMD into a
game-ready GLB:
- the original skeleton and all 7 actions;
- three LODs and a 2048² atlas;
- colour from an AI concept sheet the operator picked.

It stops at every operator decision and at every failed gate.

| Monster | Manifest | Spike root (recorded run) | Final variant | Status |
|---|---|---|---|---|
| Elite Yeti (pilot) | `tools/hdmodellib/manifests/monster/monster14.yaml` | `.review/hd-concept` | `omni-faithful-headhd-smooth2-face3-lookC2-hd` | operator: "a good candidate"; installed |
| Budge Dragon | `monster03.yaml` | `.review/hd-concept/monsters/run` | `omni-faithful-smooth2-lookC2-hd` | accepted in game, 2026-10-15; installed |
| Bloody Wolf | `monster44.yaml` | `.review/hd-concept/monsters/wolf-t2` | `t2left-reimagined-lookW3-eyes2-hd` | accepted in game, 2026-10-16; installed |

**Budget per monster** (measured on the pilot host, RTX 5090):

- machine: about 1.5–3 h when every stage runs (the table below);
- human: 2–10 h, mostly reviews; the Yeti's face work alone was 3–6 h.

| Stage (driver name) | Wall time | Peak VRAM | Writes |
|---|---|---|---|
| refs | seconds | Blender Eevee | `<root>/refs/<asset>/` |
| concept (18 candidates: 2 models × 3 levels × 3 seeds) | 14–16 min | ComfyUI | `<root>/<asset>/` |
| refine | 13 min | ComfyUI (SeedVR2 7B) | `<root>/gen/<concept>-hd/` |
| shape: Omni per seed + import | 30–40 s + 45–70 s | 8.6 GB | `<root>/omni/`, `<root>/gen/<concept>/shapes/` |
| shape: TRELLIS.2 + import (repair) | ~1–2 min + 52 s | 12–13 GB | `<root>/shapegen/` |
| gameready | 4–5 min | CPU | `<root>/gameready/` |
| colour: Paint 2.1 + hybrid + gap | 80 s + 2–3 min | 22.5 GB | `<root>/paint21/`, `<root>/gameready/` |
| head (optional) | ~20 min | 8.6 GB | `<root>/<asset>/head/` |
| depth | ~4.5 min | ComfyUI (Marigold) | `<root>/<asset>/depth/` |
| smooth (optional) | ~15 min | CPU + Paint | `<root>/<asset>/smooth*/` |
| face (optional) | ~25 min + 1–2 h by hand | CPU + Paint | `<root>/<asset>/facefit/`, `face*/` |
| look | ~1 min | CPU | `<root>/gameready/`, `<root>/ingame/` |
| in-game round | ~1 h | client | captures |
| install | seconds | CPU | `client/mumain-mutilate/src/bin/Data/` |

**Disk.** You need:

- weights: 122 GB required, plus 16 GB optional;
- installs: ComfyUI 19 GB without models, Omni 25 GB (20 GB without its uv cache), Paint 18 GB;
- per monster: 1–2 GB in its output root;
- the pilot's root, with every experiment: 20 GB.

`tools/hdmodel doctor` fails below 10 GiB free and warns below 30 GiB.

## 1 Host prerequisites

All of this section is checked by one command (section 1.8):
`tools/hdmodel doctor`. The list it checks is
[`tools/hdmodellib/prereqs.yaml`](../tools/hdmodellib/prereqs.yaml): every binary, install, ComfyUI node, and every
weight with its download URL (the revision is in the URL), size and sha256. This guide does not
copy that list; read the file.

### 1.1 Hardware and OS

| What | Pilot host | Requirement |
|---|---|---|
| OS | Arch Linux, kernel 7.2 (x86_64) | any Linux with an NVIDIA driver; nothing in the pipeline is distro-specific |
| GPU | RTX 5090, 32 GB (sm_120), driver 615.71.09 | NVIDIA with **≥ 24 GB** VRAM: Paint 2.1 peaks at 22.5 GB and its wrapper waits for 24 000 MiB free. The CUDA 13 (cu130) wheels below cover sm_75 … sm_120 |
| RAM | 60 GiB | ≥ 32 GiB; the GPU wrappers wait for 8 GiB available |
| CUDA toolkit | nvcc 13.4 at `/opt/cuda`, GCC 16 | only to build Paint's `custom_rasterizer`; the major version must match torch's CUDA 13 |

### 1.2 System packages

| What | Version on the pilot host | Used for |
|---|---|---|
| Python | 3.14.7 (`/usr/bin/python3`; ≥ 3.12 works) with `numpy`, `Pillow`, `PyYAML`, **`openvdb`** (Python bindings) | the tool itself; `openvdb` is used for head merge, smoothing, face edits and shape repair |
| Blender | **5.2.1 LTS** (`/usr/bin/blender`, `HDMODEL_BLENDER`) | LODs, bakes, skinning, every review render |
| ffmpeg | n9.0.1 | turntables, `spin-video` |
| `flock` (util-linux), `curl`, `git`, `nvidia-smi` | | the GPU lock, downloads, installs |
| `uv` | | the Python 3.12 venvs (uv-managed CPython 3.12.14) |

On Arch, use `pacman -S python-numpy python-pillow python-yaml openvdb blender ffmpeg uv`. On
other distributions, install the same packages. `openvdb`'s Python module is the one that is
often missing: `python3 -c 'import openvdb'` must work.

### 1.3 Paths: the pilot host and the generic equivalent

| Item | Pilot host (host-specific) | Generic | Override |
|---|---|---|---|
| ComfyUI | `~/ai/ComfyUI`, system unit `comfyui.service` | any folder; `python main.py --listen 127.0.0.1 --port 8188` | `HDMODEL_COMFY_ROOT`, `HDMODEL_COMFY_URL` |
| ComfyUI models | `~/ai/ComfyUI/models` (a mount of a model cache) | `<ComfyUI>/models` | (follows the root) |
| Hunyuan3D-Omni | `~/ai/hunyuan3d-omni` | any folder | `HUNYUAN_OMNI_ROOT` |
| Hunyuan3D-Paint 2.1 | `~/ai/hy3dpaint` | any folder | `HY3DPAINT_ROOT`, `HDMODEL_XATLAS_PYTHON` (`<paint>/.venv/bin/python`) |
| GPU lock | `$XDG_RUNTIME_DIR/mutilate/gpu.lock` (host-wide; the spike's installed `gpu-run.sh` still default to slot 5's spike lock, see 1.7) | the same | `HDMODEL_GPU_LOCK`; the tool passes it to the wrappers as `OMNI_GPU_LOCK`, `HY3DPAINT_GPU_LOCK` |
| ComfyUI's network | namespace `vpn3`; agent shells run in `vpn2` | the host network | see 1.6 |
| `tools/mumodels` | `$WS/tools/mumodels` | the workspace's own | `MUMODELS` |

### 1.4 ComfyUI

- **Version.** ComfyUI **0.38.0**, `https://github.com/Comfy-Org/ComfyUI` at
  `8cfe5e1ecb97512dea8deaac15e1228d7e6feeb1`.
- **Python.** Its own venv: Python 3.12, torch 2.14.0+cu130.
- **Nodes.** Every node class the pipeline uses is core: Qwen-Image 2.1, FLUX.2 Klein, SeedVR2,
  Marigold v2, MoGe, TRELLIS.2, Pixal3D and the mesh post-processing nodes. **No custom node is
  needed.** The pilot host also has a local `custom_nodes/auto_unload_after_run`. It unloads
  models when the queue drains, which helps the VRAM waits of the GPU wrappers, but it is not
  required.

The pilot install was not re-run on a clean host. The generic steps are ComfyUI's own:

```sh
(git clone https://github.com/Comfy-Org/ComfyUI ~/ai/ComfyUI && cd ~/ai/ComfyUI
git checkout 8cfe5e1ecb97512dea8deaac15e1228d7e6feeb1
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python --index-url https://download.pytorch.org/whl/cu130 'torch==2.14.0+cu130' torchvision torchaudio
uv pip install --python .venv/bin/python -r requirements.txt
exec .venv/bin/python main.py --listen 127.0.0.1 --port 8188)   # keep it running (own terminal); loopback only
```

On the pilot host it is the system unit `comfyui.service`, started on demand with
`sudo systemctl start comfyui` (host-specific). Starting it is a host-level action: an agent
asks the operator and does not start it on its own after a failed `doctor`. Its drop-in
`/etc/systemd/system/comfyui.service.d/vpn3.conf` sets `NetworkNamespacePath=/run/netns/vpn3`.

### 1.5 Weights

Every file, with its source URL at a pinned revision, its size and sha256, is in
`tools/hdmodellib/prereqs.yaml` (`weights:`). It lists 34 files:

- ComfyUI: Qwen-Image 2.1, FLUX.2 Klein 9B-KV, SeedVR2 7B, 4x-UltraSharpV2, Marigold v2 on
  Qwen-Image-Edit-2509, TRELLIS.2, plus optional MoGe-3, Pixal3D and BiRefNet;
- Hunyuan3D-Omni and DINOv2-large;
- Hunyuan3D-Paint 2.1, DINOv2-giant and RealESRGAN.

Their origins on the pilot host: `~/ai/downloads-2026-10-13/{fetch-comfy.sh,comfy.sha}`
(Marigold, MoGe), spike 2's `downloads/{fetch.sh,fetch.log}` in slot 5's `.review/hd-geometry/`
(TRELLIS.2, Pixal3D) and the two installs' `download-weights.*`. The loop below replaces them.

Fetch everything that is missing, resumable, with each sha256 checked before the file is moved
into place:

```sh
cd $WS
python3 - <<'EOF' > /tmp/hd-weights.txt
import os, yaml
p = yaml.safe_load(open("tools/hdmodellib/prereqs.yaml"))
roots = {"comfy": os.path.expanduser(os.environ.get("HDMODEL_COMFY_ROOT", "~/ai/ComfyUI")) + "/models",
         "omni": os.path.expanduser(os.environ.get("HUNYUAN_OMNI_ROOT", "~/ai/hunyuan3d-omni")) + "/models",
         "paint": os.path.expanduser(os.environ.get("HY3DPAINT_ROOT", "~/ai/hy3dpaint")) + "/models"}
for w in p["weights"]:
    if w["required"]:          # drop this line to fetch the optional ones too
        print(w["url"], roots[w["root"]] + "/" + w["path"], w["sha256"])
EOF
while read -r url dest sha; do
  [ -f "$dest" ] && [ "$(sha256sum "$dest" | cut -d' ' -f1)" = "$sha" ] && { echo "present $dest"; continue; }
  mkdir -p "$(dirname "$dest")"
  curl -fL --retry 5 -C - -o "$dest.part" ${HF_TOKEN:+-H "Authorization: Bearer $HF_TOKEN"} "$url" &&
    [ "$(sha256sum "$dest.part" | cut -d' ' -f1)" = "$sha" ] && mv "$dest.part" "$dest" && echo "ok $dest" ||
    echo "FAILED $dest"
done < /tmp/hd-weights.txt
```

- `black-forest-labs/FLUX.2-klein-9b-kv` is a gated repository. Accept its terms on Hugging
  Face and export your own `HF_TOKEN` for the download. Never write a token into a file of this
  repository.
- Its sha256 in the list is the pilot host's file, because the hub hides the digest of gated
  files. The four pre-spike files (Qwen-Image 2.1, FLUX.2 Klein, SeedVR2, UltraSharpV2) were
  matched against the hub revision in their URL on 2026-10-16.
- Omni and Paint also need their small config files. Their `download-weights.*` scripts
  (section 1.7) fetch those along with the weights, so on a new host run those scripts for the
  two installs; the loop above is enough for ComfyUI.

### 1.6 ComfyUI's network namespace

On the pilot host ComfyUI runs in the network namespace `vpn3`. Agent shells run in `vpn2`, so
`curl http://127.0.0.1:8188` fails from an agent shell (host-specific).

- `tools/hdmodel` handles this itself for the commands that talk to ComfyUI: `concept`,
  `concept-refine`, `shape-generate`, `head-generate`, `depth-marigold` and `depth-moge`
  (`hdmodellib/comfynet.py`). When `127.0.0.1:8188` does not answer, the command
  re-runs itself in the ComfyUI process's namespace through `tools/hdmodellib/incomfy.sh` and
  prints a line saying so. This needs passwordless `sudo -n nsenter` and `runuser`, which the
  pilot host has.
- Run any other command there by hand: `tools/hdmodellib/incomfy.sh <command> [args…]`.
- `doctor` reports `ComfyUI at … (netns)` when ComfyUI answers only through this path.
- **Without a namespace** (the generic case), ComfyUI listens on the host's loopback and
  nothing of this applies. Without `sudo -n nsenter`, run `tools/hdmodel` from a shell that is
  already in ComfyUI's namespace.
- The GPU wrappers' `POST /free` to ComfyUI silently fails from another namespace. They then
  wait until ComfyUI unloads its models by itself (the auto-unload node or its own idle
  unload).

### 1.7 Generator installs (Hunyuan3D-Omni, Hunyuan3D-Paint 2.1)

Both are upstream clones at a pinned commit, with a uv venv on Python 3.12 and
torch 2.14.1+cu130. The local runners and install scripts are not upstream code. They are kept
byte for byte in [`tools/hdmodellib/host/`](../tools/hdmodellib/host/README.md); that README also
lists the host-specific lines inside them. No upstream file is patched: Paint's
`LOCAL-PATCHES.md` on the pilot host says the custom camera schedule lives in
`tools/hdmodellib/paint21_audit.py`, which imports `paint.py` unchanged.

```sh
H=$WS/tools/hdmodellib/host
# --- Hunyuan3D-Omni (stage 4 shape, stage 7 heads)
(set -e; O=~/ai/hunyuan3d-omni; mkdir -p $O && cd $O
git clone --filter=blob:none --no-checkout https://github.com/Tencent-Hunyuan/Hunyuan3D-Omni.git upstream
git -C upstream sparse-checkout set --no-cone '/*' '!/assets/'
git -C upstream checkout 4d47c0cc2bd0c4281963a7314ab330a5af36bfa8
cp $H/hunyuan3d-omni/* .
sed -i "s#/home/<pilot-user>#$HOME#g" install-torch.sh download-weights.sh   # host-specific prefix
./install-torch.sh          # .venv: Python 3.12, torch 2.14.1+cu130, requirements-omni.txt
./download-weights.sh)      # Omni + DINOv2-large (+ BiRefNet into ComfyUI), sha256-checked; prints DONE
# --- Hunyuan3D-Paint 2.1 (stage 6 colour; its venv also provides xatlas for every UV atlas)
(set -e; P=~/ai/hy3dpaint; mkdir -p $P && cd $P
git clone --filter=blob:none --no-checkout https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1.git upstream
git -C upstream sparse-checkout set --no-cone '/*' '!/hy3dshape/tools/' '!/hy3dpaint/train_examples/' '!/assets/example_images/' '!/assets/qrcode/'
git -C upstream checkout 82920d643c0dc2f7bfd7255f45f62d386edfe60c
cp $H/hy3dpaint/* .
sed -i "s#/home/<pilot-user>#$HOME#g" download-weights.sh download-weights.py
export UV_CACHE_DIR=$PWD/.uv-cache UV_HTTP_TIMEOUT=600
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python --index-url https://download.pytorch.org/whl/cu130 'torch==2.14.1+cu130' 'torchvision==0.29.1+cu130'
uv pip install --python .venv/bin/python -r requirements-hy3dpaint.txt
uv pip install --python .venv/bin/python --no-build-isolation 'basicsr==1.4.2' 'realesrgan==0.3.0' 'numpy==1.26.4' \
  'torch==2.14.1+cu130' 'torchvision==0.29.1+cu130' --extra-index-url https://download.pytorch.org/whl/cu130 --index-strategy unsafe-best-match
(cd upstream/hy3dpaint/custom_rasterizer && PATH=/opt/cuda/bin:$PATH CUDA_HOME=/opt/cuda TORCH_CUDA_ARCH_LIST=12.0 MAX_JOBS=8 \
  uv pip install --python ../../../.venv/bin/python --no-build-isolation .)     # TORCH_CUDA_ARCH_LIST = your GPU's compute capability
(cd upstream/hy3dpaint/DifferentiableRenderer && PY=../../../.venv/bin/python && \
  c++ -O3 -Wall -shared -std=c++11 -fPIC $($PY -m pybind11 --includes) mesh_inpaint_processor.cpp \
  -o mesh_inpaint_processor$($PY -c "import sysconfig;print(sysconfig.get_config_var('EXT_SUFFIX'))"))
./download-weights.sh)      # Paint 2.1 + DINOv2-giant + RealESRGAN; prints DONE
```

The **GPU lock.** Exactly one GPU job runs at a time, and all of them share one host-wide lock
file, `$XDG_RUNTIME_DIR/mutilate/gpu.lock` (`HDMODEL_GPU_LOCK` overrides):

- **the tool's commands** take it themselves (`shapes.gpu_lock`, Blender in `spin-video`);
- **the wrappers** (`gpu-run.sh` in each install) take `OMNI_GPU_LOCK` / `HY3DPAINT_GPU_LOCK`.
  `tools/hdmodel` sets both to its own lock before it starts a wrapper, so a run never needs
  them exported. Their in-script default only matters when you start a wrapper by hand: the
  copies in `tools/hdmodellib/host/` default to the host-wide path; the pilot host's installed
  copies still default to spike 2's lock in slot 5 (replacing them is a host edit for the
  operator).

During the move from the spike, keep one lock file across old and new tools: while a spike
command may still run, point the new tool at the spike's lock
(`export HDMODEL_GPU_LOCK=$HOME/projects/mutilate-5/.review/hd-geometry/gpu.lock`, host-specific).

`tools/hdmodel doctor` fails when a wrapper's lock is not the tool's lock. It reports who holds
the lock (from `/proc/locks`; it never takes it).

### 1.8 Check the host: `tools/hdmodel doctor`

```sh
cd $WS
export HDMODEL_DATA=$PWD/client/mumain-mutilate/src/bin/Data
tools/hdmodel doctor              # fast: weights by size; ~5 s
tools/hdmodel doctor --full       # also sha256 of every weight (~140 GB; 2 min on the pilot host's NVMe, longer cold)
tools/hdmodel doctor --json       # machine-readable: {"ok", "full", "summary", "items": [{status, area, what, detail, data}]}
```

It checks:
- host: system Python ≥ 3.12 and its modules; the binaries; Blender's version; RAM;
- GPU: VRAM ≥ 24 GB; who holds the GPU lock; that both wrappers take the same lock;
- disk: free space at the output root;
- ComfyUI: reachable directly or through its namespace; its version; every required node class;
- the two installs: files, upstream commit, venv Python and torch, the built extensions;
- weights: each one present with its pinned size (`--full`: also its sha256);
- repository: the client data with every manifest's BMD; this workspace's `tools/mumodels`;
  the two pilot files every look stage reads (`tools/hdmodellib/pilot/`);
- no game client running.

Every `FAIL` and `WARN` line is followed by `-> follow <document>`: the section of this guide
(or the install's own `INSTALL.md`) that installs the missing item (`prereqs.yaml` `docs:`).

The status of each item is `ok`, `FAIL` (exit 1), `WARN` (optional or advisory: an optional
weight, the lock in use, a running client) or `INFO`. What each allows:

| Result | Read-only work (`status`, `gates`, `mumodels check`, tests) | GPU stages |
|---|---|---|
| exit 0, no WARN | yes | yes |
| WARN `GPU lock … held` | yes | wait until it is free; never kill the holder |
| WARN `no game client running` | yes | quit your own client first; ask about another workspace's |
| WARN optional weight / node | yes | yes, unless your manifest uses that option (`used_by` in the JSON item) |
| FAIL (exit 1) | yes, where the failing item is not involved | no: fix it (this section) or report it |

On the pilot host, 2026-10-16 (slot 5, `add-hd-model-pipeline`):

```
tools/hdmodel doctor                                  -> 72 ok, 0 FAIL, 0 WARN, 2 INFO   (exit 0; ComfyUI reached "(netns)")
HUNYUAN_OMNI_ROOT=<empty dir> tools/hdmodel doctor    -> exit 1: FAIL omni "Hunyuan3D-Omni install …"
                                                         -> follow ~/ai/hunyuan3d-omni/INSTALL.md; §1.7
```

The spike's `--full` run (all 34 weights "sha256 ok", 2 min 4 s) is in the spike root's
`reproduce/doctor-full.json`.

## 2 Repository side

### 2.1 Getting the code

The pipeline is mainline's `tools/hdmodel` with its package `tools/hdmodellib/` and tests
`tests/hdmodel/`; any mainline checkout or slot has it. The spike's original code stays on the
branch `hd-geometry-spike` (private origin, and the bundle in mainline's
`data/jobs/2026-10-16-spike-hd-guided-geometry/`) as history.

The client data (`client/mumain-mutilate/src/bin/Data`) comes from the private client clone.
It is never copied out, and neither is anything under `.review/`: it is derived Webzen art.
Never commit `.review/`.

### 2.2 The slot model

Work happens in a slot (`docs/slots.md`); generation in mainline is possible but blocks its
admin work. The spike ran in slot 5 (`feature hd-geometry-spike`), the import and the install of
the three monsters in slot 5 again (`feature add-hd-model-pipeline`). Start every session with
`tools/slot status`. There is one writer
per working tree: two people or agents use two slots. A slot's stack and clients are not needed
for stages 1–12; stage 13 (in game) runs in a slot with a running stack and a client build
(section 4).

### 2.3 Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `HDMODEL_DATA` | the workspace's client tree `src/bin/Data` (resolved through `tools/workpackage`) | the original BMDs, read only. **Export it**: the tests and every command outside a resolvable workspace need it |
| `HDMODEL_OUT` | `$WS/.review/hd-models` | the default output root; `monster … --root` overrides it per run. It also holds the rig renders `refs/<asset>/` and `compare/glb/<asset>/orig.glb` |
| `HDMODEL_GPU_LOCK` | `$XDG_RUNTIME_DIR/mutilate/gpu.lock` | the shared GPU lock (1.7) |
| `HDMODEL_CLIENT_TREE` | the workspace's client tree | the client tree `install` targets; it refuses anything but `$WS/client/mumain-mutilate` |
| `HDMODEL_MONSTER` | `monster14` | the monster a single command works on (the driver sets it per step) |
| `HDMODEL_PICKS` | | a run's `--pick` overrides (the driver sets it) |
| `HDMODEL_BLENDER`, `HDMODEL_COMFY_URL`, `HDMODEL_COMFY_ROOT`, `HDMODEL_XATLAS_PYTHON` | `/usr/bin/blender`, `http://127.0.0.1:8188`, `~/ai/ComfyUI`, `~/ai/hy3dpaint/.venv/bin/python` | tool locations (`tools/hdmodellib/settings.yaml`) |
| `HUNYUAN_OMNI_ROOT`, `HY3DPAINT_ROOT` | `~/ai/hunyuan3d-omni`, `~/ai/hy3dpaint` | the generator installs |
| `OMNI_GPU_LOCK`, `HY3DPAINT_GPU_LOCK` | set by the tool to its lock | the wrappers' lock (1.7) |
| `MUMODELS` | `$WS/tools/mumodels` | `tools/mumodels` for the `game-copy-check` gate and `install` |

**Pilot files.** Every monster's look stage reads two committed files from
`tools/hdmodellib/pilot/`: `calibration.json`, the preview calibration of the client's
lighting (copied into each run's `look/calibrate11/`), and `glb_max_texture.py`, which writes
the game copy (maps capped at the client's 2048 limit). Nothing needs seeding.

### 2.4 Unit tests

```sh
HDMODEL_DATA=$PWD/client/mumain-mutilate/src/bin/Data python3 -m unittest discover tests/hdmodel
```

This runs about 350 tests in a few seconds, CPU only: no GPU, no ComfyUI, no network (one
test runs Blender for a measure pass; one skips unless a Yeti run's refined refs are in the
output root). They include
`test_doctor.py`, which checks among other things that every model file and node class of
`tools/hdmodellib/workflows/*.json` is listed in `prereqs.yaml`. Run them after every change
under `tools/hdmodellib/`.

### 2.5 Resource rules

These rules come from `AGENTS.md` and the spike's own practice:

- One GPU job at a time, through the lock. Never wrap the driver in another `flock`. Never start
  a GPU job beside a running one.
- Kill a process only by its explicit PID, and never another session's job.
- Poll long runs in waits of 60 s or less, each with a done check: the driver's log ends in
  `monster <asset>: stages … done` or in a `MANUAL stop` / `FAIL at` block.
- Never overwrite **recorded** outputs or GLBs (the three monsters' roots, section 0). The driver
  skips steps whose outputs exist. Within **your own** attempt root, a resumed or `--from` run
  rewrites the outputs of every step after the first one that runs: that is expected there.
  Give every new attempt a new root (`mkdir -p .review/hd-models/repro && R=$(mktemp -d
  $PWD/.review/hd-models/repro/<asset>-XXXX)`); resume an attempt with the same root. `--force` is for your own roots only.
- `refs` writes `refs/<asset>/` inside the run's root, so every root renders its own (seconds).
- No game client runs while generating (`doctor` warns about it). Quit clients when you are
  done with them.
- The pipeline builds no .NET and no client code. If you build the client for the in-game check
  (section 4), follow the client build limits in `AGENTS.md` (`CMAKE_BUILD_PARALLEL_LEVEL=8`,
  one build at a time).

## 3 Re-run the three monsters

### 3.0 How the driver behaves (read once)

```sh
tools/hdmodel monster <asset> status [--root DIR]
tools/hdmodel monster <asset> run [--root DIR] [--from STAGE] [--to STAGE] [--reuse-from DIR [--reuse KIND …]] [--pick KEY=VALUE]
```

- **Stages,** in order: `refs concept refine shape gameready colour head depth smooth face look
  ingame`. A step whose outputs exist is skipped. Once a step has run, every later step runs
  again.
- **Exit codes.** `run` exits:
  - **2** at a MANUAL stop. It prints what to review and which manifest field to fill. Fill it
    and run again.
  - **1** at a FAIL, either a failed step or a failed gate. It prints the gate, a hint and
    `<root>/<asset>/driver-logs/<stage>-gates.json`.
  - **0** when the selected stages are done.
- **Gates are stops.** A FAIL ends the run. The only way past a FAIL is an operator decision
  recorded in the manifest's `gates.decisions`, `{"<stage>/<gate id>": "<who, when, why>"}`.
  The gate stays FAIL with its value, the report prints `OPERATOR DECISION: …` next to it, and
  the run continues. Never write a decision the operator did not make.
- **State and logs.** The state is `<root>/<asset>/driver-state.json`; the logs are in
  `<root>/<asset>/driver-logs/`.
- **`--reuse-from DIR`** copies the GPU outputs (concept sheet, refined refs, Omni and TRELLIS.2
  shapes, head candidates, Marigold normals, and Paint when its input LOD0 is byte-identical)
  from another root instead of generating them. It never writes into `DIR`. It is **not**
  GPU-free: Paint re-runs whenever the LOD0 differs (it did in every regression so far), so
  a reuse run takes the GPU lock.
- **Roots.** Use one root per lineage. The driver refuses two monsters with the same
  `names.prefix` in one root, and a root used with other `--pick` overrides.

### 3.1 What a re-run reproduces

**The deterministic stages are bit-reproducible.** These are refs, concept-prep, the imports,
head merge, game-ready LODs from the same mesh, the look and the game copy. Two checks:

- the Yeti regression gave a bit-identical Omni import and head merge;
- re-running the Wolf's eye-joint edit and 1024 copy gave the recorded sha256 values exactly
  (2026-10-16; 3.4).

**The AI stages are not:**

- Qwen and FLUX concepts, SeedVR2 refine, TRELLIS.2, Paint 2.1 and Marigold vary with the
  ComfyUI build, the GPU and the driver;
- Omni reproduced its mesh exactly for the same seed and inputs on the pilot host.

Two ways to re-run, and what to compare in each:

1. **Regression (exact inputs).** Run with `--reuse-from <the original root>` so the GPU outputs
   are copied, then compare against the recorded run:
   - the **gate table** (`tools/hdmodel gates <variant>`): no new FAIL, and the values within
     the spreads below;
   - the **silhouette IoU** values the gates print;
   - the **review sheets** side by side.

   The Yeti regression's spread against the pilot, with Paint re-run on new UV charts:

   | Value | Spread |
   |---|---|
   | LOD0 / LOD2 IoU vs dense | ±0.003 / ±0.006 |
   | skin score | ±0.0001 |
   | head share | ±0.002 |
   | lumpiness | ±0.001 |
   | strain | ±0.0005 |
   | gap SSIM | ±0.005 |
   | gutter step | stays ≤ 2 |
   | calibrated preview, pilot vs re-run | SSIM 0.876, p50 / p95 within 0.002 |

   The atlas-space texture SSIM is low by construction, because the UV layouts differ. Do not
   compare textures pixel by pixel.
2. **From scratch (no reuse).** Every AI stage generates new images and shapes, so the
   manifest's recorded picks name *new* files. Before you rely on them:
   - **Re-review every MANUAL decision**: the concept sheet, the shape seed, the head and the
     face landmarks. The driver does not stop for picks that are already set.
   - To make it stop, empty the field in your working copy of the manifest (`picks.concept`,
     `picks.omni_seed`, `picks.head_candidate`, `face.landmarks`).
   - The face passes and the Wolf's eye-joint targets are MU coordinates measured on the old
     mesh. Measure them again.

   Then judge the result by the gates (no FAIL without an operator decision) and the review
   sheets against the concept. Do not compare numbers one to one.

Start every re-run in a **new root**, so the recorded roots stay untouched:

```sh
cd $WS
export HDMODEL_DATA=$PWD/client/mumain-mutilate/src/bin/Data
S=$HOME/projects/mutilate-5/.review/hd-concept     # the spike root (host-specific; the recorded runs)
tools/hdmodel doctor || exit 1
```

### 3.2 Elite Yeti (`monster14`, the pilot)

**Recorded picks.** All are in `monster14.yaml`:

| Pick | Value |
|---|---|
| concept | `qwen-faithful-s22` (G1: "loved") |
| Omni seed | 2, point control, front view |
| head | `omni-s2` |
| face landmarks | 11 |
| smoothing | 5a and 5a2 |
| face passes | `face2` and `face3` |
| look | `lookC2` |
| lighting | `null` (operator 2026-10-16; the spike planned sky 0.35, normalScale 1.8) |
| in-game verdict | "a good candidate" (2026-10-14) and the plug-in decision (2026-10-16) |

The pilot root itself was built command by command, before the driver existed (stage commands:
[reference, Stages](hd-model-pipeline.md#stages)). Its driver status therefore shows `open`
steps. The driver-made reproduction is the regression:

```sh
mkdir -p .review/hd-models/repro && R=$(mktemp -d $PWD/.review/hd-models/repro/monster14-XXXX)
tools/hdmodel monster monster14 run --root $R --reuse-from $S --to look
tools/hdmodel monster monster14 status --root $R
HDMODEL_OUT=$R tools/hdmodel gates omni-faithful-headhd-smooth2-face3-lookC2-hd
```

The spike's Yeti refs used spike 1's upscaled (qwen 4×) texture; this tool renders the refs from
the original texture, so a fresh Yeti concept run sees different inputs than the pilot did.
The regression is unaffected: the concept and every later AI stage are copied by `--reuse-from`.

Where it stops, and the expected result:

- **No MANUAL stop.** Every pick and the in-game verdict are set, so even `--to ingame` runs
  through.
- **Gates.** Expect PASS for every measured gate, with the values of the pilot's column in the
  [gate table](hd-model-pipeline.md#gates-in-one-command) within the spreads of 3.1. The
  `game-copy-check` gate runs `tools/mumodels check` on the game copy itself.
- **Recorded regressions** (spike root):
  - `regress/monster14`, made before hybrid v3: one FAIL, `gap-seam-excess` 1.23. Hybrid v3 then
    made seam levelling the default.
  - `regress/monster14-v3`: PASS 50, FAIL 0, MISSING 3, MANUAL 9; seam excess 0.117 (pilot
    0.82).
  - the mainline tool's run (`add-hd-model-pipeline` 5.1): see that change's design, "Result".
- **Time.** About 1.5 h of machine time with reuse, because Paint re-runs.

### 3.3 Budge Dragon (`monster03`, root `monsters/run`)

**Recorded picks:**

| Pick | Value |
|---|---|
| concept | `qwen-faithful-s22` (operator 2026-10-15, demo sheet "concept B") |
| Omni seed | 1, point control, front view (`stages.shape.seeds` default `[1, 2]`) |
| wings | a generated part (`meshes[1] generated: true, skin_limbs: true`); no card |
| head and face passes | off (operator: small mob at ×0.5) |
| smoothing | 5a and 5a2 (defaults) |
| look | `lookC2` |
| lighting | none |

```sh
mkdir -p .review/hd-models/repro && R=$(mktemp -d $PWD/.review/hd-models/repro/monster03-XXXX)
tools/hdmodel monster monster03 run --root $R --reuse-from $S/monsters/run
```

The run **stops at `gameready` with exit 1**, on four FAILs:

| Gate | Value | Threshold |
|---|---|---|
| `dense-silhouette-iou` | 0.7021 | ≥ 0.85 |
| `dense-chamfer` | 0.013 | ≤ 0.010 |
| `dense-components` | 2 | ≤ 1 |
| `lod-closed` | 2/2/2 | ≤ 1 |

The concept redraws the dragon more upright with bigger wings, so the BMD-silhouette gates fail
by design. The recorded run (2026-10-15) continued with `--from colour` on the operator's go,
before `gates.decisions` existed. The operator's in-game acceptance ("wings are fine",
2026-10-16) is now recorded in the Dragon's `gates.decisions` for the two shape FAILs; see
`add-hd-model-pipeline` task 5.2 for the run through the mainline tool. For any FAIL the
manifest does not cover, ask the operator; their decision, in their words, goes into
`gates.decisions`, then run again. Do not pass FAILs with `--from`, and never write a decision
the operator did not make.

Expected gates after that, from the recorded `driver-logs/*-gates.json`:

| Stage | Recorded values |
|---|---|
| refine | IoU 0.9805, SSIM 0.9571, shift 1 |
| colour | evidence 0.9726, concept-dominant 0.5287, gap SSIM 0.5339, head 0.7062, detail 0.6618, blotch 27.8, seam +0.23 |
| depth | tilt 2.55 / 9.20 |
| smooth | closed 1, IoU 0.9954, lumpiness 0.0295, strain 0.0019 |
| look | gutter 0.17 / 0.11 / 0.32, every preview gate PASS |

- **In game:** `stages.ingame.verdict` is set, so the driver finishes. The spike's 1024 copy is
  `ingame/omni-faithful-smooth2-lookC2-hd-1024.glb` (recorded sha256
  `d2346a5b7d84be6a6aa11f4b56ff7011a556029b56429a864cf1751180498df1`); the mainline tool writes
  the 2048 game copy `…-2048.glb` (the 2048 master's maps already fit, so it equals the master's
  content).
- **Remaining known issue:** a small light spot at each wing root, a texture seam (operator:
  not fixed).

### 3.4 Bloody Wolf (`monster44`, root `monsters/wolf-t2`)

**Recorded picks:**

| Pick | Value |
|---|---|
| concept | `qwen-reimagined-s11` ("concept C") |
| shape | `shape: {generator: trellis2, view: left, trim_ground: 0.04, repair: {voxel: 0.4, close: 2.5, foot_radius: 0.03}}`, seed 1; the operator picked it from 13 candidates in `monsters/wolf-shape/` |
| LODs | `budgets.lod_triangles: [16000, 5000, 2000]`, `lod_max_genus: 60` |
| mane, straps | generated parts |
| head, face passes, smoothing | off |
| colour | `register_views: true`, a `part_masks` entry `blades`, `depth_filter: false` |
| look | `lookW3` |
| decisions | 2 shape and 5 colour `gates.decisions` |
| final variant | `…-eyes2-hd`: effect joints 11/12 moved onto the eyes |

The recorded run reused the concept, refine and TRELLIS.2 outputs of `monsters/run`. Reproduce
it the same way:

```sh
mkdir -p .review/hd-models/repro && R=$(mktemp -d $PWD/.review/hd-models/repro/monster44-XXXX)
tools/hdmodel monster monster44 run --root $R --reuse-from $S/monsters/run
tools/hdmodel monster monster44 status --root $S/monsters/wolf-t2     # the recorded state
```

- **No MANUAL stop.** Every pick and the in-game verdict are set. Seven FAILs carry the
  operator's decision (`FAIL+decision`), as the manifest records:
  - shape: IoU 0.7167 and Chamfer 0.0154, both measured against the BMD (IoU against the
    concept 0.737);
  - colour: evidence 0.9457, concept-dominant 0.4382, gap SSIM 0.4529, detail 0.2682, blotch
    46.26 ("2 then in-game").
- **Every other gate PASSes**, with these recorded values:

  | Gate | Value |
  |---|---|
  | refine | 0.9755 / 0.9689 / 1 |
  | non-manifold, components | 0 / 1 |
  | LOD0 / LOD2 IoU | 0.9854 / 0.966 |
  | skin score, torn attack | 0.013 / 0.0 |
  | head texel density | 15.47 |
  | gap head SSIM | 0.7297 |
  | seam excess | −0.13 |
  | tilt | 4.41 / 10.57 |
  | gutter | ≤ 0.52 |
  | look preview gates | all PASS |

- **The eye joints (post-step, by hand).** The client draws the Wolf's blue eye trails at
  joints 11/12 (`eye01`/`eye`; MoveEye). The final variant moves those two unweighted joints
  onto the HD eyes, in a new file:

  ```sh
  SRC=$S/monsters/wolf-t2                            # read only (or your own root after a re-run)
  OUT=$(mktemp -d /tmp/wolf-eyes2.XXXX)              # a new, empty folder; in your own root use
                                                     # $R/gameready/t2left-reimagined-lookW3-eyes2-hd (must not exist)
  HDMODEL_MONSTER=monster44 tools/hdmodel glb-move-joints $SRC/gameready/t2left-reimagined-lookW3-hd/model.glb \
      --out $OUT/model.glb \
      --targets '{"eye": [18.87, -67.64, 70.32], "eye01": [-4.67, -68.02, 70.89]}' > $OUT/move-joints.json
  python3 tools/hdmodellib/pilot/glb_max_texture.py $OUT/model.glb $OUT/1024.glb --max 1024
  sha256sum $OUT/model.glb $OUT/1024.glb
  cmp $OUT/move-joints.json $SRC/gameready/t2left-reimagined-lookW3-eyes2-hd/move-joints.json
  ```

  Expected (verified 2026-10-16 from the recorded input): `model.glb`
  `984e7d1250756cfa1a142d66e11d9b33e97044f7462171e4083b3d11f60f27c1`, `1024.glb`
  `d2e791be92481cd712d4035d5dc508f66d0399041ec9a06bf2385ebfa4abb7dd` (the recorded
  `ingame/t2left-reimagined-lookW3-eyes2-hd-1024.glb`), and `cmp` silent.

  - The targets come from `monsters/wolf-t2/eyes2/targets-symmetric.json`: the +x amber eye,
    2.5 MU out along its normal, mirrored for the other eye. They are only valid for this mesh.
    For a new mesh, measure the eyes again. The measuring scripts (`eyes2/find_eyes.py`,
    `visibility.py`) are ad hoc and not in `tools/`.
  - Note that `glb-move-joints` refuses an existing `--out` and refuses joints with skin
    weights. The eyes2 variant has no `metrics.json`, so `gates` does not evaluate it. Its
    gates are those of `t2left-reimagined-lookW3-hd`, because the mesh is byte-identical.

### 3.5 Checking a recorded result without the GPU

These commands only read (or write to `/tmp`). They are safe beside a running GPU job:

```sh
tools/hdmodel monster monster44 status --root $S/monsters/wolf-t2
HDMODEL_OUT=$S/monsters/wolf-t2 tools/hdmodel gates t2left-reimagined-lookW3-hd --asset monster44
HDMODEL_OUT=$S/monsters/run tools/hdmodel gates omni-faithful-smooth2-lookC2-hd --asset monster03
HDMODEL_OUT=$S tools/hdmodel gates omni-faithful-headhd-smooth2-face3-lookC2-hd          # the Yeti, pilot root
tools/mumodels check $S/monsters/wolf-t2/ingame/t2left-reimagined-lookW3-eyes2-hd-1024.glb
```

What the spike's tool printed on the pilot host (2026-10-16), the summary line last. The mainline
tool counts a FAIL with an operator decision as `FAIL+decision` (the spike printed `OPERATOR`),
and the Dragon's two shape FAILs now carry the operator's decision:

| Command | Summary | Exit |
|---|---|---|
| Wolf `gates t2left-reimagined-lookW3-hd` | `PASS 31  FAIL 0  MISSING 19  MANUAL 6  OPERATOR 4` | 0 |
| Dragon `gates omni-faithful-smooth2-lookC2-hd` | `PASS 38  FAIL 2  MISSING 14  MANUAL 7` | 1 |
| Yeti `gates omni-faithful-headhd-smooth2-face3-lookC2-hd` | `PASS 52  FAIL 0  MISSING 1  MANUAL 9` | 0 |
| `mumodels check` on the Wolf's eyes2 1024 copy | `ok` | 0 |

**Exit codes.** `gates` exits 1 when a FAIL without an operator decision is present; FAILs that
carry a decision do not change the exit code.

- **The Dragon's two FAILs** are `dense-silhouette-iou` 0.7018 and `dense-chamfer` 0.0131, the
  shape FAILs of 3.3 on the final lineage; with the recorded decision `gates` exits 0.
- **The Wolf shows 4 OPERATOR rows, not 7.** The 2 shape decisions and the coverage and
  dominance decisions apply. The other three decided colour gates read MISSING here: for a look
  variant, `gates` reads them from the pre-look colour (the depth variant), where `gap` was
  never run.
- **The Yeti's one MISSING was `model-lighting`.** The pilot GLB has no per-model lighting key;
  its manifest now sets `lighting: null`, so the gate has nothing to compare.

**Reading `monster … status`.** The Wolf's recorded root prints (2026-10-16, header shortened):

```
monster monster44 (Bloody Wolf, Monster/Monster44.bmd, MODEL_BLOODY_WOLF x2.2)
  picks: concept qwen-reimagined-s11, omni seed 1, head None
  lighting: none (Look.json globals); candidate GLB: none
  candidate t2left-reimagined-lookW3-hd

stage      status   steps  gates (P/F/M/MAN)  note        (the mainline tool prints P/F/D/M/MAN)
refs       done     1/1    -
concept    done     4/4    1/0/0/1            reused: concept
refine     done     1/1    3/0/0/0            reused: concept-refine
shape      done     3/3    -                  reused: trellis2-left-s1
gameready  done     3/3    13/0/0/1
colour     done     3/3    2/0/0/1
head       skipped  0/5    not run            head.enabled false
depth      done     4/4    3/0/0/1
smooth     skipped  0/3    not run            stages.smooth.skip
face       skipped  0/3    not run            face.enabled false (no readable face)
look       done     3/3    10/0/2/1
ingame     done     1/1    0/0/1/1
```

| Column | Meaning |
|---|---|
| `status` | `done` (every step's outputs exist and no recorded gate FAIL), `failed` (outputs exist, a recorded gate FAIL), `blocked` (the next step is a MANUAL field that is empty), `open` (some steps done), `todo` (none done), `skipped` (the manifest disables the stage; the note says why) |
| `steps` | steps whose outputs exist (MANUAL steps: whose field is set) / steps of the stage |
| `gates (P/F/D/M/MAN)` | the counts the driver recorded for this stage's gates: PASS / FAIL without decision / FAIL with an operator decision / MISSING / MANUAL (the spike's recorded roots show P/F/M/MAN and hid decided FAILs: the Wolf's gameready had 2, its colour 5; see `driver-logs/<stage>-gates.json`). `-` = the stage has no gates; `not run` = no record |
| `note` | the next step, the MANUAL field, the FAIL list, or `reused: <steps>` copied by `--reuse-from` |

- `candidate` is the look variant the driver builds (Wolf: `t2left-reimagined-lookW3-hd`).
  Post-steps such as the eyes2 joint move do not appear there.
- `candidate GLB: none` means the GLB carries no lighting key. `no GLB` means the file does not
  exist yet.
- Below the table, `status` prints the in-game verdict and the install record.

**MISSING rows** in a `gates` table:

- a skipped stage (head, smooth, face) reads MISSING;
- `gap-*` reads MISSING when no `gap` was measured on the variant's pre-look colour (the
  Wolf's depth variant);
- `look-zoom-*` reads MISSING because `look-review` is a pilot-only review sheet.

The driver's own per-stage reports are `<root>/<asset>/driver-logs/<stage>-gates.json`.

**To repeat a deterministic step,** write its output to a new `/tmp` folder and compare sha256
values (as in 3.4). A driver run with `--reuse-from` in a new root also works, but it is not
GPU-free (3.0).

### 3.6 The old-vs-new video

```sh
HDMODEL_MONSTER=monster44 tools/hdmodel spin-video \
    --hd $S/monsters/wolf-t2/gameready/t2left-reimagined-lookW3-eyes2-hd/model.glb \
    --out /tmp/wolf-old-vs-new.mp4          # add --frames 30 for a quick test of the first 30 frames
```

- **The output.** Original on the left, HD on the right, each spinning in place. They walk for
  5 s, then play attack 1 for 5 s. The video is 2560×1440 at 30 fps, CRF 14, on a grey
  background.
- **The GPU.** The command takes the GPU lock: one Blender at a time. The frame folder (about
  1 GB) is deleted after encoding.
- **The original.** The left model defaults to `compare/glb/<asset>/orig.glb` in the output
  root, written once from the BMD with its original textures (one mesh, no LOD names; the
  Blender script uses its only skinned mesh). You can also pass `--orig`.
- **Recorded videos:**
  - Wolf: `monsters/review/monster44/t2/wolf-old-vs-new.mp4` (spike root);
  - Dragon: `monsters/review/monster03/video/dragon-old-vs-new.mp4` (spike root);
  - Yeti (mainline tool, 2026-10-16): `.review/hd-models/review/monster14/yeti-old-vs-new-full.mp4`
    in slot 5; the spike's attempt had failed on the one-mesh original.

## 4 The in-game check

The only absolute truth on how a candidate looks is the game. Slot 2 ran every in-game round
(the Yeti rounds 1–3, the Dragon, the Wolf s3 and t2, the eyes variants) and handed its
procedure, helpers and findings over in a package (2026-10-16):

- the spike root's `slot2-handoff/` (ignored by Git; also in mainline's
  `data/jobs/2026-10-16-spike-hd-guided-geometry/slot2-handoff/`):
  `README.md`, `INGAME-CHECK.md` (the full procedure), `FINDINGS.md` (what was learnt, with
  every number), `INVENTORY.md` (what slot 2 holds and where it is preserved), `patches/` (the
  per-model lighting experiment), `scripts/` (helpers, plus the verbatim `/tmp` originals),
  `reference/`.
- The helpers are in the repository: [`tools/hdmodellib/ingame/`](../tools/hdmodellib/ingame/README.md).
- The captures of every round: the spike root's `ingame/captures/` (one README per round; an
  identical copy is in mainline `data/media/hd-guided-spike/ingame-captures/`).
- Two kinds of check: **4.1** a candidate through a developer overlay (`MU_DATA_OVERLAY`), before
  the operator's verdict; **4.2** the installed data, after `install`, without an overlay.

### 4.0 What the client must have

| Piece | Where | Needed for |
|---|---|---|
| GLB monster models through `Data/Models/ModelFiles.json` (empty by default), searched first in `MU_DATA_OVERLAY` (read once at start); embedded PNG base colour and normal map; four-weight GPU skinning; LOD0–2 with an optional per-entry `lod` key; the shared playback rule; loader validation (a refused file keeps the BMD) | **mainline**: OpenSpec `add-glb-monster-models`, fully landed (spec `openspec/specs/glb-models`; client main `cc9b7c57`+, mainline pin `22d6c8b0`). Proof: `slot2-handoff/patches/landed-proof/` | every in-game check |
| `tools/mumodels` (`check`, `export`, `compare`, `budget`), `tools/muctl anim-lab`, `tools/animtrace` | **mainline** | every in-game check |
| GLB textures up to 2048 × 2048 drawn; a larger image is refused by the GLB decoder | **mainline** since OpenSpec `upload-large-model-textures` (client `fce0408a`; spec `glb-models`). Before it the client drew at most 1024 × 1024, which is why the spike tested `-1024.glb` copies | test the `<variant>-2048.glb` game copy (or the 2048 master) |
| per-model lighting: `asset.extras.mu.lighting` in the GLB, `"lighting"` in a `ModelFiles.json` entry, the `Look.json` keys `lighting.diffuse.sky` / `lighting.normalScale`, and `tools/mumodels check` validation of the GLB key | **only** the preserved `skinned-lighting-experiment` commits (client `1911c693`, 4 commits; superproject `f941188`). They are in `slot2-handoff/patches/` as `format-patch` series and bundles, and as local branches in slot 2; on no remote. `patches/README.md` says how to apply them (`git am -3`; 0004 needs the three-way fallback on today's main) | a GLB that carries `lighting`. On mainline an entry's `lighting` logs "unknown field, ignored" and the GLB key is not read. No shipped candidate carries the key; the Yeti's manifest value (0.35, 1.8) exists only in its manifest and a round-3 test overlay |

**Where to run it.** In any workspace whose client has the GLB loader (mainline's client does),
from its root. The helpers drive the checkout of the **current directory**:

```sh
HD=$PWD/tools/hdmodellib/ingame                             # the helpers
. $HD/env.sh                                                # SLOT_ROOT, SCRATCH, OVERLAY_ROOT, OUT, MUCTL, HOST_WRAP
```

`env.sh` defaults (all overridable; [`tools/hdmodellib/ingame/README.md`](../tools/hdmodellib/ingame/README.md)):
- scratch under `$XDG_RUNTIME_DIR/hd-ingame` (else `/tmp/hd-ingame`): raw shots, records,
  overlays, plates;
- `OUT` = `$SCRATCH/out`. Point it at a **new** capture folder for a round
  (`.review/hd-models/ingame/captures/<round>/`), never at a recorded one;
- the client log `$SLOT_ROOT/client/mumain-mutilate/out/build/linux-x64/src/Release/MuError.log`;
- `HOST_WRAP=host.sh` when the shell is in an agent network namespace (below).

### 4.1 In-game check (from slot 2)

A candidate, before it is installed, through a developer overlay.

The steps of `slot2-handoff/INGAME-CHECK.md`, with its helper for each. Raw commands are given
too, so each step can be done by hand. `L="$MUCTL"` (= `tools/muctl --client lab`, wrapped).

1. **Check the GLB offline.**
   ```sh
   sha256sum <root>/ingame/<variant>-2048.glb                     # compare with the handoff you send
   tools/mumodels check <root>/ingame/<variant>-2048.glb --json
   ```
   Exit 0, and read: the model name and source BMD, conventions 1, joints = the BMD's bones
   (Yeti 51, Wolf 41), LOD0/1/2 with one node each, clips action00–06, no texture above 2048.
   **The opaque atlas must be an RGB PNG**: the client takes alpha from the PNG colour type, so
   an RGBA PNG is alpha-tested with culling off even when every texel is opaque (section 7).
2. **Build and start the stack** (`AGENTS.md` resource rules: one client build at a time):
   ```sh
   export CMAKE_BUILD_PARALLEL_LEVEL=8
   tools/dev client build && tools/dev up      # a fresh database is seeded with the test accounts
   ```
   Runtime commands (`tools/dev up`, `client run`, `tools/muctl`, `tools/animtrace run`) refuse
   inside an agent's network namespace (`ip netns identify $$` prints `vpn2`) and print the
   remedy `sudo nsenter --net=/proc/1/ns/net --mount=/proc/1/ns/mnt --wd="$PWD" -- runuser -u
   $USER -- <cmd>`. `tools/hdmodellib/ingame/host.sh <cmd>` is that line; `env.sh` puts it into
   `HOST_WRAP` and `$MUCTL` when a namespace is detected.
3. **Account.** OpenMU seeds its test accounts into an empty database. Use **`testgm` /
   `testgm`**, character **`testgmDk`** (a level-400 GM Dark Knight: `/hide`, `/move` and
   teleport work; it carries healing potions). `trace start` and `animtrace run` need it idle at
   full health: `$HD/heal.sh`.
4. **The overlay.** A folder that mirrors `Data/`, with a byte copy of the candidate and its
   `Data/Models/ModelFiles.json`:
   ```sh
   $HD/make-overlay.sh monster44-t2 <root>/ingame/<variant>-2048.glb MODEL_BLOODY_WOLF Monster/Monster44.glb --lod-pins
   ```
   ```json
   {"formatVersion": 1, "models": [{"model": "MODEL_BLOODY_WOLF", "file": "Monster/Monster44.glb"}]}
   ```
   Entry keys: `model` (the client's `MODEL_*` name = the manifest's `client.model`), `file`
   (path under `Data/` = the manifest's `bmd` with `.glb`), optional `lod`
   (`{"screenHeights": [...], "hysteresis": h}`), optional `actions`
   (`{"2": {"clip": "walk", "crossfade": 3}}`; default clip `actionNN`), and `lighting` only
   with the patches. An unknown key is a warning and is ignored; an unknown model or a missing
   file is an error. Keep overlays under `$SCRATCH`, not in the repository. `--lod-pins` also
   builds `<name>-lod0/1/2` (step 8).
5. **Start the lab client and prove the GLB is drawn.**
   ```sh
   $HD/lab-start.sh $OVERLAY_ROOT/monster44-t2 glb     # or `none` for the BMD; logs in, marks the log position
   $HD/log-check.sh glb                                # exit 1 on a refusal
   ```
   By hand: `MU_DATA_OVERLAY=<overlay> tools/dev client run --name lab`, then `$L login testgm
   testgm` and `$L select-char testgmDk` (`MU_NONE=1` for the BMD). Use `config.ini`
   `[Render] Look=Enhanced` and a 1024 × 768 window, as every recorded round did. **Pass:**
   `MuError.log` has, since the start,
   `Model MODEL_BLOODY_WOLF is drawn from <overlay>/Data/Monster/Monster44.glb` and no line
   containing `not used`, `could not be loaded` or `ModelFiles.json:`. Any of those is a
   refusal and the BMD is drawn instead. `anim-lab bones` and trace manifests name the BMD file
   even when the GLB is drawn: they are no proof.
6. **Place the monster** on a lab tile without grass:

   | Map | Tile | Use |
   |---|---|---|
   | **Chaos Castle 1** | map 18, 30,95 | the default for every monster (`LAB_SPOTS[18]` in `tools/animtracelib/run.py`); plain floor; the black floor rectangles are the map's |
   | Devias | map 2, 160,60 | the Yeti's home look (rounds 1–3) |
   | Lorencia | map 0, 114,50 | avoid: tall grass stands in front of small monsters and holes the planar shadow |
   | Crywolf Fortress | map 34, 172,228 | only the Wolf's chrome pass; `anim-lab play` fails there, so shots are live |
   | Raklion | map 57, 223,211 | the animation-trace matrix location (step 11) |

   ```sh
   MON=60 $HD/lab.sh setup        # /hide, teleport, heal, quiet trace, spawn, one idle tick, overlay off
   ```
   By hand: `$L say /hide`; `$L teleport 30 95 --map 18`; `$HD/heal.sh`;
   `$L trace start --seed 1 --map 18 --x 30 --y 95 --quiet-view --keep`;
   `$L anim-lab spawn --monster 60 --x 30 --y 95 --rotation 2`;
   `$L anim-lab play --model-action 0 --ticks 2`; `$L overlay off`. `MON` is the **server**
   monster number (Yeti 20, Dragon 2, Wolf 60). During a trace the player's own character is
   not drawn, only puppets.
7. **Frozen frames.** `MON=60 $HD/lab.sh play <action> <ticks> <name>`
   (`anim-lab play --model-action A --ticks T --freeze-at-end`) prints the last tick's frame.
   **BMD and GLB must reach the same frame at the same tick**, or the comparison is invalid.
   Poses used: Wolf idle 0/10 (frame 2.75), walk 2/8 (3.06), attack1 3/9 and attack2 4/9 (3.30);
   Yeti walk 2/4 (1.40). Contact sheets: Wolf walk ticks 2, 5, 8, 11, 14, 16; attacks 3, 6, 9,
   12, 15, 18 (an attack lasts 21 ticks).
8. **LOD pinning.** No lab command exists; the three pinned overlays of step 4 do it:
   `screenHeights` `[]` pins LOD0, `[100, 0.000001]` LOD1, `[100, 50]` LOD2. The client picks
   the LOD from the projected height of the model's box as a fraction of the window height:
   default `screenHeights` [0.2, 0.1], hysteresis 0.1 (coarser below `screenHeights[i]`, finer
   again only above `screenHeights[i] × 1.1`). To name the LOD the unpinned client drew, shoot
   the same frozen pose and camera with each pin and run
   `$HD/lod-compare.py $OUT <glb mask> <unpinned> <lod0> <lod1> <lod2>`: the pin that is about
   100 % exact is the active one.
9. **Cameras and captures.**

   | Camera | Command |
   |---|---|
   | default | `$L camera --mode default` (angles −48.5, 0, −45) |
   | zoom 700 | `$L camera --yaw 45 --pitch -20 --distance 700` (front three-quarter) |
   | zoom 600 | `--distance 600`: the minimum; a ×2.2 Wolf no longer fits |
   | behind / right / left | yaw 225 / 135 / 315 at 700 |

   `$HD/lab.sh shot <name> default|45,-20,700` writes `$OUT/<name>.png` (a quality-100 JPEG
   converted losslessly). Shoot the BMD and the GLB in **separate client sessions** at the same
   tile, pose and camera. **Background plate:** in the same frozen instant remove the puppet,
   shoot, respawn and replay the pose: `$HD/lab.sh plate <name> <camera>`. The whole standard
   set is one command per session:
   ```sh
   MON=60 $HD/session.sh bmd none full
   MON=60 $HD/session.sh glb $OVERLAY_ROOT/monster44-t2 full
   for p in 0 1 2; do MON=60 $HD/session.sh lod$p $OVERLAY_ROOT/monster44-t2-lod$p lod; done
   ```
   `session.sh` uses the Wolf's poses: edit them for another monster. Clean up with
   `$L freeze off; $L anim-lab remove; $L trace stop; $L camera --mode default`.
10. **Brightness.** The mask is the pixels whose max RGB channel differs from the plate by more
    than 12, minus near-black pixels (max channel < 10: the planar shadow), after a 3 × 3
    opening. Luma = PIL `L` / 255 inside it. Report p50, p95, std and the pixel count, GLB
    against BMD on the same frame and camera, at the default camera **and** zoom 700:
    ```sh
    python3 $HD/brightness.py $OUT $PLATES chaoscastle1-enhanced-{bmd,glb}-{idle,walk,attack1}{,-zoom}
    ```
    The recorded values per monster are in the troubleshooting table (section 6) and
    `FINDINGS.md` §4. Run on copies of the Wolf t2 plates, this command reproduces that table
    exactly (2026-10-16).
11. **Animation-trace diff.** Each set in a **fresh** client session, idle at full health at
    Raklion 223,211:
    ```sh
    export ENTRIES="$(for a in 00 01 02 03 04 05 06; do echo mon-060-bloody-wolf-map57-a$a; done)"
    $HD/trace.sh bmd none
    $HD/trace.sh glb $OVERLAY_ROOT/monster44-t2
    $HOST_WRAP tools/animtrace diff $CAP_WORK/trace-bmd $CAP_WORK/trace-glb
    ```
    Entries come from `tests/animation-trace/matrix.json`
    (`mon-<server number>-<name>-map57-a<action>`). `diff` reports only the first difference per
    entry; for a variant that moves bones on purpose (the eye joints) use
    `$HD/trace-compare.py` to list and attribute every differing field.
12. **Quit and record.** `$L quit`, `tools/dev down`; never leave a client running. Write the
    round's README in the new capture folder (client commit, overlay `ModelFiles.json`, shots,
    the "is drawn from" line, measurements), as the recorded rounds do.

**Pass/fail** (the criteria slot 2 applied):

| Area | Pass |
|---|---|
| Loading | `mumodels check` exit 0 and the sha256 matches the handoff; "is drawn from <overlay>" logged with no refusal line |
| Animation | `tools/animtrace diff`: `N entries, 0 differing (tolerance 0.01, 0 masks)`, exit 0 (bones, frames and every spawn's position, angle, scale and light within 0.01). Exception: bones moved by design; then only those bones and the spawns descending from them differ. Frozen frames: BMD and GLB on the same `frame` at every tick |
| By eye (Chaos Castle set: default, 700, 600 where it fits) | no tears at joints, straps or wing roots over a stride and an attack contact sheet; nothing missing or see-through from behind or the sides; no seams; effects (fire, eye trails) at the BMD's place and **visible** |
| Brightness | masked p50 close to the BMD's: the Wolf t2 within ±0.008 (accepted); the Wolf s3 0.07 below (rejected) |
| LOD | the active LOD at the lab cameras is named; the pinned LOD1 and LOD2 have no holes |
| Per-model lighting (only with the patches) | G1: no per-model value and global (0, 1) is pixel-identical to the unpatched client (bar the band over animated background); G2: values in the file give the same image as the same global values, a per-model value replaces the global one, the entry wins over the GLB key by key, a bad value is refused and the BMD drawn; G3: BMD-drawn models in the same frame do not change (`captures/round3/per-model/README.md`) |

13. **MANUAL.** The operator judges the captures against the BMD and gives a verdict, which goes
    into `stages.ingame.verdict`.

### 4.2 Install, then the in-game check of installed data

Only after the operator's verdict is in `stages.ingame.verdict`, and only in a workspace whose
client tree is the private clone `client/mumain-mutilate` (mainline, an idle slot or a `feature`
job; never a `pr`/`branch` job, whose client tree is the public fork):

```sh
tools/hdmodel monster monster44 install --glb <the accepted GLB>    # default: <root>/ingame/<candidate>-2048.glb
tools/hdmodel monster monster44 status | tail -2                     # the verdict and the install record
git -C client/mumain-mutilate status --short                         # the GLB and Models/ModelFiles.json
```

`install` refuses, writing nothing, when the client tree is not the private clone, the monster
has no verdict, `tools/mumodels check` refuses the GLB, the GLB names another `MODEL_*`, or a
map exceeds the client's 2048 limit. It records `stages.install` (source, sha256, date) in the
manifest and commits nothing: commit the two data paths in the private clone (explicit paths)
and move the superproject pin with a message that says why. The models are never wired into
the public fork or an upstream pull request.

Then check the installed data in game, **with `MU_DATA_OVERLAY` unset**:

1. `sha256sum client/mumain-mutilate/src/bin/Data/Monster/MonsterNN.glb` equals
   `stages.install.sha256`; `tools/mumodels check` on it exits 0.
2. Build the client from this tree (`export CMAKE_BUILD_PARALLEL_LEVEL=8; tools/dev client
   build`; the build copies `src/bin/Data` beside `Main`), `tools/dev up`.
3. Start the lab client on its own data: `$HD/lab-start.sh none glb` (overlay argument `none`;
   `env -u MU_DATA_OVERLAY tools/dev client run --name lab` by hand), then
   `$HD/log-check.sh glb`. **Pass:** `MuError.log` has
   `Model MODEL_<NAME> is drawn from …/Data/Monster/MonsterNN.glb` (the build's own `Data/`, no
   overlay path) for every installed model, and no refusal line.
4. Shoot the accepted round's tile, pose and camera (4.1 steps 6–9) and compare by eye and by
   the masked brightness of step 10 with the accepted captures in
   `data/media/hd-guided-spike/ingame-captures/` (Yeti `round3/`, Dragon `monster03/`, Wolf
   `monster44-t2-eyes2/`).
5. Quit the client (`$L quit`) and `tools/dev down` when done.

## 5 Add a new monster

Worked example: **monster02, the Hound** (Lorencia, server monster 1).
The spike root's `monsters/candidates.md` maps ten candidates with their difficulty.

### 5.1 Read the original

```sh
export HDMODEL_DATA=$PWD/client/mumain-mutilate/src/bin/Data
(cd tools && python3 -c "import sys; sys.path.insert(0, '.'); from pathlib import Path; from hdmodellib import mudata, config
b = mudata.load_bmd(config.data_root() / 'Monster/Monster02.bmd')
print('meshes', [m.texture for m in b.meshes]); print('bones', [x.name for x in b.bones]); print('actions', len(b.actions))")
```

The Hound has three meshes (`hound_head01.jpg`, `hound_head02.jpg`, `hound_lower.jpg`, no
alpha) and 36 bones on a Biped rig, with `Bip01 Head` as the head bone. Its weapons are separate
BMDs; leave them alone.

Client values come from the client sources (`client/mumain-mutilate/src/source/`):

| File and place | Value | Hound |
|---|---|---|
| `Engine/Object/ZzzCharacter.cpp`, CreateMonster (`case MONSTER_HOUND`) | `Object.Scale`, `HiddenMesh`, weapons | 0.85; `HiddenMesh = 0`; sword |
| `Engine/Object/ZzzCharacter.cpp`, `case MODEL_HOUND:` | `Weapon[n].LinkBone` | 19, 14 = `Bone_left`, `bone_right` |
| `Engine/Object/ZzzOpenData.cpp`, OpenMonsterModel | play speeds, BoneHead | defaults, BoneHead 5 |
| `Core/Globals/_enum.h` | `MONSTER_MODEL_<NAME>` (`client.index`), the `MODEL_*` name (`client.model`) | 1, `MODEL_HOUND` |

- **Play speeds.** OpenMonsterModel's defaults are `[0.25, 0.2, 0.34, 0.33, 0.33, 0.5, 0.55]`.
  A per-model `switch` after them overrides the walk speed for some monsters (the Yeti 0.28,
  the Dragon 0.7).
- **Weapon link bones go into `bones.sockets`.** The weapons are separate BMDs; leave them
  alone.
- **`HiddenMesh`.** A BMD shared by two monsters hides one mesh per monster: the Hound hides
  mesh 0 and the Hell Hound mesh 1. Both head meshes then show in the rig renders, one over the
  other. The manifest has **no field to drop a mesh** (see section 7). Ask the operator before
  you build such a monster.

### 5.2 Write the manifest

Copy the closest manifest to `tools/hdmodellib/manifests/monster/monster02.yaml`:
- a biped with a face: `monster14.yaml`;
- a quadruped: `monster44.yaml`;
- winged: `monster03.yaml`.

The schema and every field are in
[`tools/hdmodellib/manifests/README.md`](../tools/hdmodellib/manifests/README.md). Then set:

1. **Identity.** `kind: monster` (required; the only supported kind), `asset: monster02` (it
   must equal the file name), `label`, `bmd`,
   `texture_dirs`, `pose: [0, 0]` and `client.{model, index, scale, play_speed,
   hold_last_actions}`.
2. **`meshes`.** Every BMD mesh is `body`. An original alpha mesh (wings, mane, straps, rags) is
   a **generated part**: `{index, texture, role: body, name, generated: true}`, plus
   `skin_limbs: true` when its bones sit on another mesh, as the Dragon's wing spars do. Do not
   use `card`: it is a legacy fallback (D12, "a model contains all its see-through parts").
3. **`bones.*`** from the bone list.
   - `head` is the head bone first, then the bones that ride on it. With no head bone, use
     `head.enabled: false` and `bones.head: []`.
   - Also fill `sockets` (bones the client attaches effects to: they must survive),
     `limb_roots`, `hands`, `feet` and `smooth_exclude`.
   - The data test checks that every bone exists in the BMD.
4. **`concept.subject` / `detail`.** Describe the original's **real** colours and parts, as
   seen in the rig renders of 5.4's first command (`refs`, which needs no concept words). The
   Wolf's draft said "blood-red armoured wolf" for a brown wolf with bandage straps, and the
   Dragon's said "purple" for a red-orange dragon.
5. **Clear everything the copied monster's operator decided.** These are not yours to inherit:
   - picks: `picks: {concept: null, omni_seed: null, head_candidate: null}`,
     `face.landmarks: {}`, `face.passes: []`;
   - `gates.decisions: {}` and `stages: {}` (drops `ingame.verdict`, `install`, `smooth.skip`,
     seeds);
   - `shape:`, `colour:` and `budgets` back to the defaults (delete the blocks; the Yeti's
     `budgets` are a fair start);
   - `look:` back to the pilot's `lookC2`, `lighting: null`;
   - the comments, which describe the other monster.
6. **Head and face.** Start with `head.enabled: false` and `face.enabled: false`, then decide
   after the first build (5.4). `face.enabled` needs a face that reads at the game camera ×2.
7. **`names.prefix`.** Set it if another monster in the same root uses the same default
   (`omni-<level>`).

   `concept.subject`/`detail` may stay rough until the refs exist (5.4); they are prompt words,
   and the schema accepts any text.
8. Check the manifest:
   ```sh
   tools/hdmodel monster monster02 status --root $PWD/.review/hd-models/m02
   python3 -m unittest discover -s tests/hdmodel -p 'test_monsterspec.py'
   ```
   `status` loads and validates it (an unknown key or a wrong type is refused, naming the key).
   The tests check bones and meshes against the BMD.

### 5.3 Shape input by body plan (decide before stage 4)

Shape generators read a single image, so pick the view in which the body plan is legible.

| Body plan | Shape source | Why |
|---|---|---|
| upright biped (Yeti, Hound) | the default: Omni on the **front** view with the BMD as point control (no `shape:` block) | the front view shows both arms and legs. The Yeti's s2 kept the limbs separate, so the animation holds |
| quadruped, or long forward parts (Wolf) | `shape: {generator: trellis2, view: left}` (or Omni on `view: left`) | the Wolf lesson: from the front, the long blades point at the camera and Omni made one short tusk out of four. The side view kept 4 long blades and the spiky mane (IoU against the concept 0.737, against 0.598 for Omni front) |
| winged, upright (Dragon) | Omni front worked | the wings spread across the front view |

Shape notes:

- **Repair.** TRELLIS.2 needs `repair: {voxel: 0.4, close: 2.5, foot_radius: 0.03}`. Raw, it is
  not manifold, and direct decimation refuses it. With `close: 0.6` the Wolf's rib cage stayed
  hollow (section 6). It may also need `trim_ground` (a fraction of the height) against a
  generated ground slab.
- **Several candidates.** Generate several seeds (`stages.shape.seeds`) and review them
  against the **concept**, not the BMD. The BMD silhouette gates fail for any concept that
  changes the outline; the operator's pick is then recorded in `gates.decisions`.
- **Multi-view input** is not a working option yet. Pixal3D 4-view fused a ground slab. The
  plan to retry is in mainline `docs/todo/med-prio/hd-monster-multiview-shape-input.md`.

### 5.4 Run to the first MANUAL stop, then stop by stop

```sh
R=$PWD/.review/hd-models/m02
tools/hdmodel doctor > /tmp/doctor.txt; echo "doctor exit $?"; grep 'GPU lock' /tmp/doctor.txt
# exit 0 and "free": refs renders with Blender Eevee (GPU for seconds; refs takes no lock)
tools/hdmodel monster monster02 run --root $R --to refs     # $R/refs/monster02/, ~3 s
# look at $R/refs/monster02/sheet-lit.png: whole monster, centred, nothing cropped, limbs clear;
# now write concept.subject/detail from what you see (5.2 step 4)
tools/hdmodel monster monster02 run --root $R               # GPU from here (ComfyUI, the lock)
```

`refs` is skipped once its outputs exist. If you change `pose`, `meshes` or the BMD afterwards,
remove `$R/refs/<asset>/` (your own output) before you run again.

The second `run` generates the concept candidates (about 15 min of GPU), then stops with exit 2
at the first MANUAL stop. **Planning without the GPU ends before that `run`**: you have the
manifest (validated by `status`), the rig renders and the list of decisions below, and the
first MANUAL stop is reached only after the concept GPU step. Each MANUAL stop pairs a review
with the field the operator fills; the fill-in only comes from the operator.

A shared BMD with `HiddenMesh` (5.1; the Hound) is an operator decision **before** the concept:
the concept would redraw both meshes. Stop there and ask.

| Stop | What to review | Field the operator fills |
|---|---|---|
| **concept** (G1) | `<root>/monster02/sheet-{faithful,remaster,reimagined}.png` beside `original.png`; ComfyUI workflow `hd-models/monster02-1-concepts` | `picks.concept` (`<model>-<level>-s<seed>`) |
| **shape** (G3) | each seed's `align.json` and clay views | `picks.omni_seed` |
| **head** (G6, only with `head.enabled`) | `head/candidates-sheet.png` | `picks.head_candidate` |
| **face** (only with `face.enabled`) | the clay renders beside the close-up | `face.landmarks` (read by eye; 1–2 h) |
| **ingame** | the captures (section 4) | `stages.ingame.verdict` |

- **Concept pick, G1.** "Is this the monster, only better?" Stop the whole monster if no sheet
  is loved: every later stage only gets closer to the concept.
- **Operator choices between stops, recorded in the manifest:**
  - `head.enabled` and `face.enabled`. The Wolf: "get the model good before focusing on head".
    The Dragon: a small mob, so no head and no face.
  - `stages.smooth.skip: true` when the Yeti presets melt detail (the Wolf's straps, muzzle and
    spikes).
  - the look parameters: `lookW3` keeps the Wolf as bright as the BMD, where `lookC2` darkened
    it.
- **Gate FAILs stop the run.** Read the gate report. Then either fix the cause (another seed,
  part masks, `register_views`, …) or ask the operator. Only the operator's decision goes into
  `gates.decisions`.
- **Colour problems to expect with a changed concept:**
  - `colour.register_views: true` when the concept cells are larger than the shape: the Wolf's
    were 1.2–1.6×;
  - `colour.part_masks` against phantom paint (section 6).

### 5.5 Finish

- Effect bones: if the client attaches effects to bones that the HD mesh moved (eye trails,
  breath), move the joints in a new file with `glb-move-joints` (3.4).
- Make the old-vs-new video (3.6) for the operator.
- Run the in-game round (section 4.1). The operator's verdict goes into `stages.ingame.verdict`.
- Install the accepted GLB into the private client and check the installed data in game (4.2).
- Commit the manifest with explicit paths (`git add tools/hdmodellib/manifests/monster/monster02.yaml`),
  and the installed data in the private clone (its two paths), then move the pin. Never commit
  `.review/`.

## 6 Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| The concept's gold blades show as gold smears on the Wolf's chest and face (phantom paint); colour gates FAIL | the concept shows parts in front of the body. Projection paints their pixels onto whatever surface the ray hits first on the model, which lacks them there | `colour.part_masks`: a hue/saturation/value key for the part (`{name: blades, hue: [28, 58], sat_min: 0.5, val_min: 0.55, overlap: 0.1, grow_mu: 0.5}`). Pixels of the part colour only the model's part. `grow_mu: 1.5` caught the mouth too (Paint's gold teeth); 0.5 with view confirmation worked. The MoGe depth filter (`colour.depth_filter`) is built but not validated: it rejected 43–75 % |
| TRELLIS.2 shape imports with thousands of non-manifold edges; LOD falls back to the voxel remesh; colour coverage FAIL with 31 % of the area seen from no direction | the raw TRELLIS.2 mesh is open (Wolf: 4183 non-manifold edges, genus ~3000). `repair.close: 0.6` left the rib cage **hollow** inside | `shape.repair: {voxel: 0.4, close: 2.5, foot_radius: 0.03}`: a solid torso with ribs and straps as relief, genus 1, 99.9 % visible. Keep `budgets.lod_max_genus` above the real handles (Wolf 60) |
| Colour gates FAIL with projection coverage ~40 % on a TRELLIS.2 or side-view shape | the concept cells are 1.2–1.6× larger than the refit shape (**unregistered concept scale**: each view was refined on its own) | `colour.register_views: true` (step `refs-register`): fits each refined view's camera to the generated shape. The Wolf's registered IoU was 0.73–0.82 |
| Quadruped comes out with merged or short forward parts (one tusk instead of four blades); in game "a completely different thing" | **Omni front view on a quadruped**: from the front, long forward parts point at the camera | the side view: `shape: {generator: trellis2, view: left}` or Omni `view: left` (5.3). Review shape candidates against the concept |
| `ComfyUI not reachable` / `curl: (7) Failed to connect to 127.0.0.1:8188`; or a command hangs before ComfyUI work | ComfyUI runs in **another network namespace** (pilot: `vpn3`; agent shells: `vpn2`), or ComfyUI is down | `tools/hdmodel` re-runs ComfyUI commands in its namespace itself (it prints a line). For other commands use `tools/hdmodellib/incomfy.sh <cmd>`. If no ComfyUI process exists: `sudo systemctl start comfyui` (pilot host) or start `main.py`. Without passwordless `sudo -n nsenter`, run from a shell inside the namespace. `tools/hdmodel doctor` says which case applies |
| A GPU step waits for a long time (`gpu-run: waiting (free VRAM …)`) | another job holds the lock, or ComfyUI keeps models in VRAM and the wrapper's `/free` did not reach it (other namespace) | wait. `doctor` names the lock holder's PID. Do not kill another session's job; never start a second GPU job beside it |
| Two GPU jobs ran at once | a `gpu-run.sh` started by hand took its default lock, or an old spike command took the spike's lock while the new tool took the host-wide one | one lock file for every tool (1.7): `HDMODEL_GPU_LOCK`, and the same path in `OMNI_GPU_LOCK` / `HY3DPAINT_GPU_LOCK` for wrappers started by hand; `doctor` FAILs on the mismatch |
| A subagent or worker died mid-run with HTTP **429** (rate limit) | the assistant's API, not the pipeline (the Wolf worker on 2026-10-15) | the driver's state survives: `monster <asset> status`, then `run` again with the same `--root`. A finished step is not repeated. Check the step log for a half-written output before continuing |
| `FAIL at shape …` / gameready stops on `dense-silhouette-iou` with a reimagined concept | the BMD-silhouette gates measure against the original, so a concept that changes the outline fails by design | get the operator's pick, then record it in `gates.decisions` (the Wolf's manifest shows the form) |
| `look` stage: `shared file …/calibration.json missing` | `tools/hdmodellib/pilot/` is incomplete | restore it from Git (`doctor` names it) |
| `install …: … private client clone client/mumain-mutilate …` | the workspace's client tree is the public fork (a `pr`/`branch` job) or another path | install from mainline or a `feature`/idle slot; never wire models into the public fork |
| `install …: no in-game verdict recorded` | the operator has not accepted the model in game | run 4.1 and ask the operator; only their verdict goes into `stages.ingame.verdict` |
| `monster run: … share the lineage prefix` | two monsters in one root with the same `names.prefix` | set `names.prefix` in one manifest, or use another `--root` |
| `monster run: … was run with pick overrides …` | a root remembers its `--pick` overrides | pass the same `--pick`, or use a new root (one lineage per root) |
| `gates: no …/metrics.json (not a game-ready variant)` | a post-step file such as `…-eyes2-hd` has no metrics | run `gates` on the variant it was made from |
| In game the model is the old BMD; `MuError.log` says `… is not used: <reason>`, `could not be loaded` or `ModelFiles.json: …` | the loader refused the GLB or the entry (parent mismatch, inverse binds not FLOAT/MAT4, float JOINTS_0, NaN, negative weights, external `uri`; an unknown model or missing file) | `tools/mumodels check`; fix the overlay entry (4.1 step 4) |
| The GLB is drawn ("is drawn from" logged) but untextured or wrong where a texture should be | a client older than `upload-large-model-textures` (client `fce0408a`) draws maps up to 1024 × 1024 only; a map above 2048 is refused by the decoder | update the client, or test a copy with maps at most the client's limit (`pilot/glb_max_texture.py --max N`) |
| An opaque HD model shows holes, see-through faces or missing backfaces in game | the atlas PNG is **RGBA**: the client takes alpha from the PNG colour type (`EmbeddedTextures.cpp`), so it alpha-tests at the fixed 0.25 with **culling off**, even when every texel is opaque. glTF `alphaMode`, `alphaCutoff`, `doubleSided` and `emissive` are ignored. The alpha state of every LOD follows **LOD0's** texture | write opaque atlases as RGB PNG (the pipeline's `body` route does); `tools/mumodels check` and `check_conventions` do not catch an all-opaque RGBA |
| An effect anchored to a bone (the Wolf's blue eye trail, `BITMAP_JOINT_ENERGY` on bones 11/12) is hidden or shows only a dim glow on the HD model | effect sprites are **depth-tested**: an HD mesh with real volume swallows sprites that sat in front of the BMD's thin cards. The Wolf's `eyes1` variant (joints at the eye centres) hid them inside the head | move the unweighted effect joints a few MU **outside** the surface: `eyes2` puts them 2.5 MU out along each eye's normal (×2.2 ≈ 5.5 world units), both sparks visible in idle and walk (3.4, `glb-move-joints`). Check with `spark-blobs.py` and the trace (4.1 step 11) |
| The Bloody Wolf looks glassy green-gold on Crywolf Fortress (map 34) | the Crywolf map draws every Bloody Wolf mesh a second time with `RENDER_CHROME \| RENDER_BRIGHT` (`GMCrywolf1st.cpp:1524-1535`); on the closed HD surface the sheen is one continuous figure, on the BMD it breaks up along the cards | expected; no missing parts or sorting problems. Whether map 34 should skip the pass for GLB models is open (section 7) |
| The candidate reads darker (or brighter) than the BMD in game although the studio preview matched | the look stage's brightness | measure with 4.1 step 10 and compare: Wolf s3 (lookC2) p50 0.196 vs BMD 0.263 at zoom 700, rejected; Wolf t2 (lookW3) within ±0.008 of the BMD in every pose and camera, accepted; Dragon (lookC2) 0.224 vs 0.263, slightly darker, accepted; Yeti lookC2 0.439 vs 0.318, brighter (+0.12). A look that darkens (the Yeti's `lookC2` on the Wolf) needs a brighter one (`lookW3`: form 0.25, ao_power 1.25, lift 0) |
| A small monster draws a coarse LOD at the default camera | the LOD follows the projected box height as a fraction of the window: default `screenHeights` [0.2, 0.1], hysteresis 0.1 (finer again only above × 1.1). The Dragon (×0.5) draws **LOD1** at the default camera, LOD0 at zoom; the Wolf (×2.2) LOD0 everywhere | check the pinned LOD1/LOD2 for holes (4.1 step 8); a per-entry `"lod": {"screenHeights": [...]}` can change it. Whether small monsters need other defaults is open |

## 7 Known gaps

- **Transparency in generated parts.** Generated parts (wings, mane, straps) are solid geometry
  in the one opaque RGB atlas. A part that needs real holes (rags, membranes with holes) would
  need its own primitive with an **RGBA PNG**: the client ignores glTF `alphaMode` and takes
  alpha from the PNG colour type, then alpha-tests at 0.25 with culling off. The alpha state of
  a mesh follows its LOD0 texture, so every LOD must carry the same alpha-ness. That export is
  not built (D12 open item). Glowing, scrolling or pulsing parts need the unbuilt `effect` role;
  `tools/mumodels check` refuses `alphaMode BLEND` (the spike root's `slot2-handoff/FINDINGS.md` §12, and
  `slot2-handoff/reference/transparent-parts-investigation.md`).
- **Effect bones and depth-tested sprites.** Whether "put a bone-anchored effect joint a few MU
  outside the surface" (the Wolf's eyes2) becomes a pipeline rule for every monster with such
  attachments, and who checks it (`mumodels check` or the capture), is open.
- **Per-model lighting is not in mainline.** Only slot 2's preserved patches carry it (4.0).
  Whether it goes to mainline, and with which values, is open: the Yeti is already brighter than
  its BMD (+0.12 p50), and its planned (0.35, 1.8) would raise p50 by another 0.008 (zoom) to
  0.020 (default). The global `Look.json` keys change every Enhanced skinned model, the player
  included; the operator chose the per-model opt-in (option b).
- **The Crywolf chrome pass** on a continuous HD surface reads glassy (section 6); whether map 34
  should skip it for GLB models is open.
- **Client draw-path gaps** (mainline, read from the code; the spike root's `slot2-handoff/FINDINGS.md` §12): a failed GPU
  submit draws nothing (the archived design says the CPU fallback draws LOD0; it does not); the
  CPU paths (`RENDER_WAVE`, shadow map, `RenderMeshAlternative`) use LOD0 only; `BlendMesh` and
  `HiddenMesh` index the GLB loader's part order, which equals the BMD's only for an exported
  original; picking and culling use a fixed box per model type, not the skinned bounds.
- **Frame time was measured for the Yeti only.** `tools/mumodels budget`, 100 Elite Yetis,
  Enhanced, whole-frame time, criterion ≤ 1.5× the BMD: the pilot GLB 1.088×
  (7.970 → 8.672 ms), the exported Yeti 1.036× (9.005 → 9.326 ms), after indexed draws and
  once-per-vertex skinning (earlier runs 1.326× and 1.61×). The Wolf's 16000-triangle LOD0 and
  the other candidates were not budgeted (reports in `slot2-handoff/reference/budget/`).
- **Multi-view shape input.** Single-image generators lose what one view cannot show. The plan
  (scale-normalised, shadow-free views for Pixal3D, Hunyuan3D-2mv) is in mainline
  `docs/todo/med-prio/hd-monster-multiview-shape-input.md`.
- **`spin-video` and one-mesh originals** (fixed 2026-10-16). The original GLB names its only
  mesh `mesh0` (no `LOD0`), and the spike's `gr_spin.py` raised `StopIteration` on it. It now
  falls back to the only mesh and otherwise names the meshes it found (unit test
  `test_spinvideo.OneMeshOriginalTest`).
- **The eye-joint measurement** (`eyes2/find_eyes.py`, `visibility.py`) is ad hoc, in the
  Wolf's root, not in `tools/`.
- **Unverified on a clean host.** The install steps of 1.4 and 1.7 are the pilot host's
  recorded steps. They were not re-run on a new machine. `doctor` verifies the result, not the
  steps.
- **No field to drop a mesh.** A monster whose BMD is shared and that hides a mesh
  (`HiddenMesh`, for example the Hound and the Hell Hound) renders both meshes in its refs and
  concept. Excluding one needs a new manifest role or field: an unbuilt decision.
- **`refs` takes no GPU lock.** It renders with Eevee for a few seconds. Run it when `doctor`
  shows the lock free.
- **Spike 1's texture for the Yeti refs.** The spike's Yeti rig renders used spike 1's upscaled
  texture (`.review/hd-spike/variants/qwen/Monster/snowman02.OZJ.png` in slot 5). The mainline
  tool always uses the original texture, so a fresh Yeti concept differs from the pilot's input
  (3.2). Upscaled reference textures may become an option if a monster needs one.

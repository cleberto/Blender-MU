HD MU Online monsters: Elite Yeti, Budge Dragon, Bloody Wolf (2026-10-16)
==========================================================================

Fan-made HD remakes of three original MU Online monsters, plus the
documentation of the AI-assisted pipeline that made them. MU Online and its
original models belong to Webzen.

Contents
--------
models/     the three HD models (GLB, glTF 2.0 binary)
docs/       how the pipeline works
              hd-model-pipeline.md    reference: stages, quality gates, settings
              hd-model-pipeline.png   the pipeline as a diagram
              hd-model-reproduce.md   step by step: host setup, re-running the
                                      three monsters, adding a new monster
agent/      instructions for AI coding agents (Claude Code, Codex, Pi, ...)
              hd-model-pipeline/SKILL.md
examples/   the real settings files of the three monsters, as worked examples
              monster14.yaml (Elite Yeti), monster03.yaml (Budge Dragon),
              monster44.yaml (Bloody Wolf), README.md (what each key means),
              prereqs.yaml (every AI model used, with source and sha256)
demo/       pictures of the process and the result (see below)
SHA256SUMS  checksums of every file

The comparison videos (original left, HD right) are posted separately.

The models
----------
- Three levels of detail as separate meshes LOD0 / LOD1 / LOD2 (triangles):
    Elite Yeti    7998 / 2500 / 1000
    Budge Dragon  6002 / 2002 /  802
    Bloody Wolf  16000 / 5000 / 2000
- Per LOD a base colour map and a tangent-space normal map (2048x2048 on LOD0).
- Skinned to MU's ORIGINAL skeleton (Yeti 51 joints, Dragon 39, Wolf 41), at
  most 4 bone weights per vertex.
- The 7 original animations, keys unchanged from the original model:
    action00 stand 1    action01 stand 2    action02 walk
    action03 attack 1   action04 attack 2   action05 hit    action06 die
- asset.extras.mu.model names the MU model it replaces (e.g. MODEL_ELITE_YETI).
- Wings (Dragon), mane and straps (Wolf) are real geometry, not alpha cards.

Viewing: Blender 4.x/5.x (File > Import > glTF 2.0; hide LOD1 and LOD2, all
three LODs sit on top of each other) or any glTF viewer, e.g.
https://gltf-viewer.donmccurdy.com/.

Game client: the standard MuMain client cannot load these files. Loading them
in game needs a GLB model loader and a texture limit of 2048 (the stock limit
is 1024); both are changes in our own client and not part of public MuMain.

The pipeline documentation
--------------------------
The docs describe the pipeline exactly as we run it: on one Linux machine with
an RTX 5090, Blender, ComfyUI and several local AI models, driven by our own
tool (tools/hdmodel). The tool itself is NOT included: it is tied to our setup
and our private repository. Read the docs as a recipe to learn from or to
rebuild in your own environment, not as a ready-to-run package. Paths such as
tools/..., .review/..., slots or "the private client" refer to our repository.

In short, per monster:
 1. render the original model from four sides;
 2. AI concept art from those renders (Qwen-Image edit), you pick one;
 3. AI 3D shape from the concept (Hunyuan3D-Omni, or TRELLIS.2 from the side
    view for four-legged monsters), you pick a seed;
 4. Blender: clean game mesh, three LODs, UVs, baked AO and normal maps,
    skinned to the original bones, original animations copied;
 5. colour: the concept projected onto the model, gaps filled by
    Hunyuan3D-Paint 2.1 and blended in;
 6. optional head, face and smoothing passes, then a final "look" pass;
 7. automatic quality gates (shape, colour, seams, LODs, skinning); a failed
    gate stops the run until a person decides;
 8. in-game check against the original (our client only).

Using it with an AI agent: give the agent agent/hd-model-pipeline/SKILL.md,
the two docs and the examples, and ask it to adapt the procedure to your
machine. The skill says where a person must choose (concept, shape seed,
in-game verdict); the agent should never choose for you.

Demo pictures (demo/)
---------------------
yeti-hd-demo.png, budge-dragon-hd-demo.png, bloody-wolf-hd-demo.png
    the original next to AI concept variants (step 2)
yeti-concept-vs-model.png      Yeti: chosen concept (top) vs final model (bottom)
wolf-concept-shape-final.png   Wolf: concept, raw AI shape (clay), final model
dragon-final-views.png         Dragon: final model, textured and clay
wolf-final-views.png           Wolf: final model, textured and clay
dragon-lods.png, wolf-lods.png the three levels of detail
in-game-original-vs-hd.png     all three in our client: original vs HD, same
                               frame and camera

# Studio Capability Audit (Phase 0)

- **Initiative:** AI-Native Game Art & Animation Production Pipeline ([README](README.md))
- **Date:** 2026-11-22. **Prepared by:** Claude Code for the Board (Board decision 2026-11-22: Claude Code performs audit, research and spikes; `director` reviews as design authority, because the `director` runtime is read-only and has no web or script access).
- **Method:** every row was checked on the studio machine or in the repositories on this date, unless marked `UNVERIFIED`. Nothing was installed for this audit.
- **Dated snapshot:** this audit records the state of 2026-11-22 before the tier-1 installs and is not kept up to date. Rows have changed since, for example background removal (BiRefNet built as `comfy-edit.py matte`, spike S7) and the tier-1 R&D models (decision D2). Current tool status: [dependencies/registry.yaml](../../../dependencies/registry.yaml) and [spike results](spikes/README.md).

Classification: **Available** (works today, tested) · **Partial** (some of it works, or the code is present but weights, permission or integration are missing) · **Missing** · **Blocked** (exists but a rule, licence or permission stops its use) · **Research** (unknown whether it can work).

## 1. Hardware and runtime

| Item | Finding | Source |
|---|---|---|
| GPU | NVIDIA GeForce RTX 3060, **12 GB** VRAM, driver 572.83 | `nvidia-smi` |
| CPU | Intel Core i5-12400F | `wmic` |
| System RAM | **16 GB** (tight: FLUX schnell fp8 is a 17.2 GB checkpoint and already loads with offloading; video and large edit models will be RAM-bound) | `Win32_ComputerSystem` |
| Disk | C: 477 GB, **85 GB free** (one video model plus a few checkpoints would use most of it) | `df` |
| ComfyUI | v0.46.0 portable, commit a277b5b, clean tree, `--listen 127.0.0.1 --offline`; custom nodes: none (only the two upstream files) | `git`, `/system_stats` |
| Checkpoints | `sd_xl_base_1.0` (SHA256 31e35c80…, CreativeML Open RAIL++-M), `flux1-schnell-fp8` (SHA256 ead42627…, Apache-2.0); no LoRA, ControlNet, VAE, upscaler, CLIP-vision, segmentation, background-removal or video weights | `models/` listing, registry |
| Godot | 4.6.3 stable | `godot --version` |
| Paperclip | 2026.1023.0, local_trusted; company Soucean (SOU) | runtime docs |

## 2. Agents, models and tool permissions

| Agent | Runtime / model | Profile | Image and engine tools allowed |
|---|---|---|---|
| `director` | Claude Code, Fable 5.1 high | read-only | none; no web search, no script execution, no GitHub credential (reads repositories and Paperclip, comments) |
| `producer`, `project-manager` | Claude Code, Sonnet 5.5 medium | read-only | none |
| `game-designer` | Claude Code, Fable 5.1 high | workspace-write | five Godot commands (import, quit/smoke, version, `--write-movie` frames, QA screenshot runner) |
| `ui-designer` | Claude Code, Sonnet 5.5 medium | workspace-write | five Godot commands; UI/UX Pro Max search |
| `qa-engineer` | Claude Code, Sonnet 5.5 medium | workspace-write | five Godot commands; reads images with its vision model |
| `game-artist` | Claude Code, Sonnet 5.5 medium | workspace-write | five Godot commands; PixelFX list/render; `art-ops.py`; `comfy-draft.py`; `comfy-edit.py` (since 2026-11-22) |
| `gameplay-programmer` | Cursor, gpt-5.3-codex-high | workspace-write (Cursor) | engine code, scenes, scripts in its write sets |
| `web-engineer` | Cursor, gpt-5.3-codex-high | workspace-write (Cursor) | web only |

There is **no** technical-artist or animator agent. Creating one is a Board decision (initiative §13).

## 3. Capability classification

### A. Art direction and concept
| Capability | Class | Evidence |
|---|---|---|
| Visual identity, style guide per project | Partial | Deckbound has an Art Bible, target-pack plan, direction records; written by agents, approved by `director`/Board. No reusable studio template beyond `knowledge/departments/game/domain/art/` |
| Concept exploration (L2 directions) | Available | SOU-71: 4 directions, comparable sheets, decision recorded |
| Moodboard from external references | Blocked | Licence rule: no outside images as generator input; text-only references |
| Turnarounds, expression sheets | Research | Not attempted; needs character consistency (see B) |

### B. Production artwork
| Capability | Class | Evidence |
|---|---|---|
| Text-to-image (SDXL, FLUX schnell) | Available | `comfy-draft.py`, pilot Tasks SOU-66, SOU-68, SOU-71 |
| Image-to-image on own art | Available | `comfy-edit.py img2img` (SDXL, FLUX), G7(c) 2026-11-22 |
| Inpainting: repaint or remove existing content | Available (one production case) | `comfy-edit.py inpaint` (SDXL); SOU-64 run 2 removed a lantern cleanly (one case, not yet a measured capability); outside-mask pixels restored exactly (tested) |
| Inpainting: **insert a new object** | **Missing** | SOU-64 run 2 (6 failures) and Board spike S1 (4 failures): 0/10 attempts on one input with SDXL base, with both latent-noise-mask and `InpaintModelConditioning` + `DifferentialDiffusion`. Needs an inpainting-trained model or another method |
| FLUX inpaint | Blocked | Refused in `comfy-edit` after poor results (no inpainting training in schnell) |
| Outpainting | Partial | Core node `ImagePadForOutpaint` present; no template, inherits the insertion limit |
| Structural control (pose, depth, lineart) | Partial | Core ControlNet nodes present; **no ControlNet weights**, no permission |
| Reference conditioning / character consistency | Missing | No IP-Adapter or reference model; core has `CLIPVisionEncode`, `StyleModelApply`, `ReferenceLatent` nodes but no weights; consistency today is "same seed + same prompt" only (SOU-64 run 1: separately generated parts did not match) |
| Per-project LoRA | Partial | Core has `TrainLoraNode`, `LoraLoader`; no trained LoRA, no training data policy, untested on 12 GB |
| Transparent / layered generation | Partial | Core has `EmptyQwenImageLayeredLatentImage`, `LayersFromBoundingBoxes`; **no Qwen-Image weights** (size and licence to be verified) |
| Background removal / matting | Partial | `art-ops key` (colour key, border-connected) works on flat backdrops; cast shadows defeat it (SOU-64-F); core `RemoveBackground` node present, no model |
| Upscaling | Partial | Core `ImageUpscaleWithModel`; no upscale model |
| Colour and palette | Partial | `art-ops grade`; no palette quantise or report (2B backlog); value range measured only by the Board (SOU-68-F01) |
| Pixel art | Partial | PixelFX effects (MIT) and `--filter nearest`; no pixel-art generator tested |

### C. Animation-ready asset preparation
| Capability | Class | Evidence |
|---|---|---|
| Masks (rect, ellipse, polygon, alpha, colour) | Available | `art-ops mask` (2026-11-22) |
| Cut parts, re-assemble, diff | Available | `art-ops compose`/`trim`/`diff`; Board recipe tested 2026-11-22 (part from master, exact alpha) |
| Semantic segmentation of character parts | Partial | Core `SAM3_Detect`, `SAM3_VideoTrack`, `WeVisOneDetect` (text-prompted segmentation) present; **no weights**; licence and quality on illustrations unknown |
| Occlusion reconstruction (paint hidden areas whole) | Research | Depends on inpainting quality; removal works, completion of hidden anatomy untested |
| Layer decomposition of a flat illustration | Research | No tool installed; candidates under research |
| Pivots, anchors, joint points | Missing | Defined manually in specs (SOU-64 parts list); no detection |
| Naming, coordinates, reassembly check | Partial | Specs and registry conventions; `diff` exists; no validator |

### D. Rigging
| Capability | Class | Evidence |
|---|---|---|
| Godot Skeleton2D rig (Bone2D, Polygon2D, AnimationPlayer) | Partial | Engine supports it (TOOL-DECISIONS D2); no rig built yet (SOU-77 waits); `gameplay-programmer` can write scenes |
| Mesh generation, skin weights, IK | Missing | No tool or script |
| Spine and other runtimes | Blocked | Spine not adopted (D3), licence cost; no other runtime evaluated |
| Rig validation | Missing | Only planned as SOU-77 checks |

### E. Animation
| Capability | Class | Evidence |
|---|---|---|
| Frame-by-frame sprite sheets | Partial | `art-ops sheet`; frames must be generated consistently (unproven for characters) |
| Skeletal keyframes authored as data | Research | Godot `.tscn`/`.tres` are text; no generator or motion library |
| Procedural / secondary motion | Missing | None |
| AI video / motion generation | Partial | Core has Wan 2.x, LTX, Hunyuan video nodes; **no video weights**; 16 GB RAM and 85 GB disk are likely limits |
| VFX | Partial | PixelFX (pixel-art effects only) |

### F. Engine integration
| Capability | Class | Evidence |
|---|---|---|
| Import, `.import` files, smoke | Available | Agents run `godot --headless --import/--quit`; CI `headless-tests-and-smoke` |
| Frame capture | Available (opaque); alpha: spike S3 | `--write-movie` and Deckbound's QA screenshot runner (scene path argument); transparent capture and headless behaviour untested |
| Animation preview/render to video or strips | Partial | `--write-movie` can render frames; no fixture scenes for assets (Phase 2D backlog) |
| Atlas/sprite-sheet packing tool | Missing | Open item in TOOL-DECISIONS |
| Animation state machine generation | Research | Engine supports AnimationTree; no generator |

### G. Visual QA
| Capability | Class | Evidence |
|---|---|---|
| Vision review of still images | Available | `qa-engineer` and `director` open images; rubric with hard gates |
| Script checks: size, alpha, budget, diff | Partial | `art-ops info`, `diff`; no luminance/value stats (SOU-68-F01), no seam detector |
| Animation QA (jitter, loops, clipping) | Missing | No rendered-animation fixtures |
| Identity drift metrics | Missing | Judged by eye only |
| CI visibility for reviewers | Partial | `qa` sees CI; read-only roles cannot (PR #96 rule) |

### H. Process and governance
| Capability | Class | Evidence |
|---|---|---|
| Task contract, review stages, Board approval | Available | Paperclip; pilot Tasks |
| Agent `blocked` disposition | Blocked | Agents cannot enter `blocked` for non-issue blockers (HTTP 422, OQ-048); every tool failure strands the Task `in_progress` until the Board acts (SOU-64 twice) |
| Provenance and licence tracking | Available | Spec provenance blocks; comfy tools print provenance with hashes |
| Cost tracking | Partial | Tokens recorded; dollar cost unavailable for handed-over runs |
| Single GitHub account | Partial | Every merge is a Board admin-merge exception |

## 4. Current bottlenecks (ranked)

1. **No inpainting-trained, commercially licensed model**: new objects and hidden anatomy cannot be added (blocks Phase 3).
2. **No character-consistency mechanism**: parts and poses generated separately do not match.
3. **No segmentation or layer-decomposition weights**: part separation is manual masking by the agent.
4. **No rigging, mesh, weight or motion tooling**: nothing between "layers" and "animation".
5. **Hardware ceiling**: 16 GB RAM and 85 GB free disk limit video and large edit models more than the 12 GB GPU does.
6. **Lifecycle friction**: tool failures strand Tasks (OQ-048); each costs a Board round.
7. **No technical-artist role**: tool research and pipeline work fall to the Board operator.

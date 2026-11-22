# Technology Research Findings and Evaluation Matrix (Phase 1)

- **Date:** 2026-11-22. Web research by three research agents working for the Board (primary sources: model cards, repositories, licence files, papers, official docs), plus checks on the studio machine. Nothing was installed or downloaded.
- **Evidence labels:** **V** the primary source was read; **U** unverified (secondary source, snippet or memory); **T** tested on the studio machine. A V licence is a reading by a research agent, not legal advice: every tool chosen for production still gets the registry security review (security-architecture §11.1) and a licence check before install.
- **Commercial filter:** running a model to make shipped game assets is commercial use. Non-commercial or research-only weights are excluded, even when outputs are "free to use".

## 1. Key findings (what changes the plan)

1. **The studio's ComfyUI already contains the nodes for most target capabilities** (T): SAM 3 detection and tracking, background removal, Qwen-Image-Layered latents, Qwen-Image-Edit text encoders, FLUX.2 latents, `InpaintModelConditioning`, `DifferentialDiffusion`, ControlNet (including inpainting ControlNet), LoRA training (`TrainLoraNode`), Wan 2.x, LTX and Hunyuan video. What is missing is **weights**, and in some cases a custom node (GGUF loaders, IP-Adapter). Capability is gated by models, licences, RAM and disk, not by ComfyUI itself.
2. **Object insertion failed for a known, fixable reason** (T + V): SDXL base is not an inpainting model; spike S1 confirmed that changing the conditioning node is not enough. Two commercially usable fixes exist: the Fooocus inpaint patch on SDXL with a grey pre-fill (weights tagged "openrail", node pack GPL-3.0; licence text incomplete), and **FLUX.2 [klein] 4B** (Apache-2.0, V), a 4B model for generation **and** reference-based editing that should fit 12 GB.
3. **Automatic layer decomposition with occlusion completion exists, but is not production-ready alone** (V): **See-through** (SIGGRAPH 2026; code Apache-2.0, weights Apache-2.0 plus OpenRAIL++-M use restrictions) turns one anime illustration into 19–23 occlusion-completed RGBA part layers with depth and draw order, on about 8–10 GB VRAM. Its authors list failure modes; expect a repair rate of perhaps 20–40% (U). **Training-data provenance is a policy question:** it was trained on 9,102 Live2D models scraped from public sites with no stated data licence.
4. **Rigging has no turnkey automatic tool**; the reliable route is our own pipeline (V): alpha → contour → constrained Delaunay mesh (CDT, MPL-2.0; avoid Shewchuk's Triangle, whose licence forbids commercial inclusion) → harmonic or BBW weights → a neutral rig JSON compiled to Godot nodes (and optionally Spine JSON). Godot 2D IK is still experimental; 4.6's new IK is 3D only, so IK is baked at authoring time.
5. **AI video is a motion reference, not a sprite source** (V/U): Apache models exist (Wan 2.x, LTX 0.9), but identity drift, no alpha, non-looping clips and minutes per clip make them unfit for final frames; 14B I2V models are marginal with 16 GB RAM.
6. **16 GB system RAM and 85 GB free disk are the binding hardware limits**, more than the 12 GB GPU (T + U): 20B Qwen models and 14B video models need heavy offloading.
7. **Licence traps found** (V): every FLUX.1 [dev] derivative (Fill, Kontext, Redux) and FLUX.2 klein 9B are non-commercial; InsightFace models (used by InstantID, PuLID, IP-Adapter FaceID) are non-commercial research only; RMBG-2.0, 4x-UltraSharp, MatAnyone and the large Depth Anything models are non-commercial; SD3.5 is free only under USD 1M annual revenue; HunyuanVideo excludes the EU, UK and South Korea; Spine's runtime terms require an editor licence per user and say a product "can't replace the Spine Editor", which needs a legal reading for agent-generated Spine JSON.

## 2. Evaluation matrix

Columns: quality evidence · automation (CLI/API/ComfyUI headless) · fits 12 GB VRAM / 16 GB RAM · licence and commercial use · maintenance · integration effort · recommendation. **Bold** = recommended for a spike.

### 2.1 Image generation and editing
| Candidate | Quality evidence | Automation | Hardware fit | Licence / commercial | Maintenance | Integration | Recommendation |
|---|---|---|---|---|---|---|---|
| **FLUX.2 [klein] 4B** (+ base for LoRA) | Comfy benchmark ~8.4–9.2 GB VRAM on a 5090 (V claim); multi-reference editing (V) | Native ComfyUI (V docs); Diffusers | Likely; Ampere has no FP8 compute (U) | **Apache-2.0** (V); 9B is non-commercial (U) | 2026 release | New weights; our ComfyUI has FLUX.2 latent nodes (T), klein loader unconfirmed | **Spike first: insertion, occlusion fill, consistency** |
| **SDXL + Fooocus inpaint patch** (Acly nodes) | Docs: grey pre-fill for new content (V) | ComfyUI custom node | Fits | Weights "openrail" (text incomplete, V); node GPL-3.0 (V) | Mature | One custom node | **Spike as the cheap fallback** |
| Qwen-Image-Edit-2511 | Best open editor by vendor claim (V claim only) | Native ComfyUI (V) | 20B: GGUF Q4/INT4 + 7B encoder; **RAM-bound** (U) | Apache-2.0 (V) | Active | GGUF/Nunchaku custom node | Spike only after a RAM decision |
| SDXL inpainting 0.1 | Weak at strength 1 (V) | ComfyUI | Fits | RAIL++-M (V) | Stale (2023) | Low | Fallback only |
| BrushNet / PowerPaint | Authors call SDXL weak / SD1.5-era | Python | Fits | Apache / MIT (V) | 2024 | Medium | Skip |
| FLUX.1 Fill/Kontext/Redux [dev], ACE++ | — | — | — | **Non-commercial** (V) | — | — | **Excluded** |
| SD3.5 | — | ComfyUI | Fits | Community licence, USD 1M cap (V) | — | — | Avoid |
| xinsir ControlNet Union SDXL / ProMax | 12 control types incl. inpaint/outpaint (V) | Native ControlNet nodes (U) | ~2.5 GB | Apache-2.0 (V) | 2024 | New weights; preprocessors need a node pack, check OpenPose weights (non-commercial, U) | **Spike for pose/layout control** |
| IP-Adapter SDXL plus | Style/identity transfer (U) | Custom node | Fits | Apache-2.0 (V) | — | Custom node | Spike after klein if needed |
| InstantID / PuLID / FaceID | — | — | — | **InsightFace non-commercial** (V) | — | — | **Excluded** |
| **Per-project LoRA** (ai-toolkit MIT, kohya Apache-2.0) | Common practice (U) | Headless CLI (V) | SDXL likely; klein-4B plausible (U); RAM tight | Permissive (V) | Active (kohya 2026-11-21, V) | Training data = approved project art only | **Spike after a consistent master set exists** |
| LayerDiffuse | Native alpha; colour shift (V) | Custom node | Fits | Apache code; weights unstated | Stalled (V) | Medium | Superseded by See-through decoder |

### 2.2 Segmentation, matting, layer decomposition, depth
| Candidate | Quality evidence | Automation | Hardware fit | Licence / commercial | Recommendation |
|---|---|---|---|---|---|
| **See-through** | LPIPS 0.155 vs 0.288 (SAM+LaMa); failure modes listed (V) | CLI + MIT ComfyUI node pack (V) | ~8–10 GB with NF4/offload (V); Windows unstated | Code Apache-2.0; weights Apache + OpenRAIL++-M restrictions (V); **scraped training data** | **Spike on Scrivener + 10 masters, after the provenance decision** |
| Qwen-Image-Layered | Merges/fragments parts per See-through authors (V); 640 px | Native ComfyUI (T node present) | 20B, RAM-bound (U) | Apache-2.0 (V) | Secondary: props/cloak splits |
| SAM 2.1 | Point/box prompts | Python | Small | **Apache-2.0** (V) | **Mask correction tool** |
| SAM 3 | Text prompts; "planar, incomplete" per See-through (V) | Native ComfyUI (T) | Fits (U) | Custom "SAM License", no non-commercial clause, gated, terminable (V) | Legal check first, else SAM 2.1 |
| See-through `l2d_sam` parser | Only open anime body-part parser found (V) | Python | Small | Apache-2.0 (V) | Use in the modular chain |
| **BiRefNet** / **ToonOut** (anime fine-tune) | ToonOut 95.3%→99.5% pixel accuracy on anime (U) | Official Comfy node (V) | ~3.5 GB | MIT (V / U) | **Master cut-out and re-matting** |
| RMBG-2.0, MatAnyone | — | — | — | **Non-commercial** (V) | Excluded |
| **Depth Anything 3 MONO-LARGE** / anime Marigold | Draw-order hints | Python | Fits | Apache-2.0 for SMALL/BASE/MONO-LARGE (V); others CC BY-NC | **Depth for z-order** |
| OpenCV, scikit-image | Classical | Python | CPU | Apache / BSD (U) | **Contours, pivots, QA** |
| RevealLayer | Scenes, FLUX.1-dev base | — | — | Non-commercial base (U) | Excluded |
| Bunraku (2026) | Illustration → layers → meshes → keyposes (V abstract) | No code released (V) | — | Paper CC BY-NC-SA | Watch |

### 2.3 Rigging, animation, engine
| Candidate | Evidence | Automation | Licence / cost | Recommendation |
|---|---|---|---|---|
| **Godot Skeleton2D / Bone2D / Polygon2D** | Weights and polygons scriptable (V); 2D IK experimental (V) | `.tscn`/`.tres` text; headless `@tool` builders | MIT, free | **Primary runtime spike** |
| Spine (editor + spine-godot) | Industry reference; physics, IK, meshes (V) | CLI export/import; documented JSON (V) | Pro USD 379 one-time per person under USD 500k revenue (V); runtime terms need legal reading; spine-godot 4.6 unconfirmed | Quality ceiling; **gated on Board + legal** |
| Blender (Python, glTF → Skeleton3D ortho) | Headless (U) | Full Python | GPL tool, outputs free | Fallback if 2D IK blocks |
| Rive, DragonBones, Live2D, Creature, Spriter | — | Poor or stalled (V/U) | Subscriptions or stale | Skip |
| Stretchy Studio (MIT), Premation (AGPL), Animated Drawings (MIT, archived) | Auto-rig references (V) | Web/desktop, not agent-drivable | — | Study code only |
| **CDT (MPL-2.0)** + harmonic weights (SciPy) / libigl BBW (MPL-2.0; Python `bbw` unconfirmed) | Standard methods | Python | Permissive (V) | **Auto mesh + weights spike** |
| Shewchuk Triangle | — | — | **No commercial inclusion** (V) | Excluded |
| Wan 2.1/2.2 (Apache-2.0), LTX-Video 0.9 (Apache-2.0) | Drift, no alpha, slow (U) | Native ComfyUI (T nodes) | 14B I2V marginal on 16 GB RAM (U) | Motion reference spike only, after RAM |
| CogVideoX-5B I2V | 720×480, 8 fps | — | Registration, 1M visits cap (V) | Avoid |
| HunyuanVideo-I2V | — | — | Excludes EU/UK/KR (V) | Excluded |
| **Godot Movie Maker** | PNG with `transparent_bg` (V); headless capture undocumented (U) | CLI (allowed to agents today) | Free | **Render-capture spike** |
| SSIM (scikit-image), LPIPS (BSD-2), mesh sanity checks, vision LLM as ranker | Standard | Python | Permissive (U) | **QA-gate spike with seeded defects** |

## 3. State of the art, honestly

- **Can do now (with the right weights):** production-grade character cut-out alpha; promptable part masks; reference-based editing and object insertion with Apache models at 4B scale; plausible occlusion-completed part layers for anime-style characters; scriptable Godot cut-out rigs.
- **Cannot do unattended yet:** guaranteed-correct hidden anatomy (plausible, not authoritative); automatic skin weights at commercial quality without iteration (every tool found assumes a human touch-up); animation appeal judged reliably by a vision model; consistent final frames from video models.
- **Therefore:** the pipeline must be *generate → decompose → validate automatically → regenerate targeted parts*, with structured QA and bounded retries, and benchmarks must measure the repair rate, not only the best case.

## 4. Sources
Key primary sources read by the research agents: FLUX.2 klein 4B card (huggingface.co/black-forest-labs/FLUX.2-klein-4B), Acly inpaint nodes (github.com/Acly/comfyui-inpaint-nodes), xinsir ControlNet Union (huggingface.co/xinsir/controlnet-union-sdxl-1.0), IP-Adapter (huggingface.co/h94/IP-Adapter), InsightFace licence (github.com/deepinsight/insightface), Qwen-Image-Edit-2511 and Qwen-Image-Layered (huggingface.co/Qwen), See-through (github.com/shitagaki-lab/see-through, arXiv 2602.03749), SAM 2 and SAM 3 (github.com/facebookresearch), BiRefNet (github.com/ZhengPeng7/BiRefNet), ToonOut (arXiv 2509.06839), Depth Anything 3 (github.com/ByteDance-Seed/Depth-Anything-3), Godot Polygon2D, 2D skeletons, SkeletonModification2D and Movie Maker docs (docs.godotengine.org), Godot 4.6 IK article (godotengine.org), Spine purchase, runtime licence, CLI and JSON format pages (esotericsoftware.com), CDT (github.com/artem-ogre/CDT), Triangle terms (cs.cmu.edu/~quake/triangle.html), libigl licence, Wan 2.x and HunyuanVideo-I2V cards, LTX licence, Bunraku (arXiv 2607.27348).

# AI-Native Game Art & Animation Production Pipeline: Board Review Package

- **Status:** `PROPOSED` for Board review (2026-11-22). No tool, model, agent or permission is added by this package.
- **Scope:** studio-wide capability (not a Deckbound feature). Deckbound and the Scrivener are the first benchmark only.
- **Prepared by:** Claude Code for the Board (Board decision 2026-11-22: Claude Code audits, researches and runs spikes; `director` reviews as design authority, because its read-only runtime has no web search or script execution).
- **Parts:** [01 Capability audit](01-capability-audit.md) · [02 Technology research and evaluation matrix](02-technology-research.md) · [03 Architecture, benchmarks, spikes, roadmap, agents, budget, risks, gates](03-architecture-and-plan.md)

## Executive summary

1. **Where the studio is.** Concept, text-to-image, image-to-image, masked repainting, masks, compositing, engine import and frame capture work today (Verified). Inserting new objects, character consistency, part segmentation, occlusion reconstruction, meshing, weights, rigging, animation authoring and animation QA do not (audit §3). The Scrivener (SOU-64) failed exactly there: separately generated parts do not match, and SDXL base cannot add a lantern (Board spike S1, 0/4).
2. **The gap is mostly models and glue, not engines.** The studio's ComfyUI already has the nodes for SAM 3, background removal, layered decomposition, instruction editing, ControlNet, LoRA training and video (Verified); weights, licences, RAM and disk are what is missing.
3. **Credible paths exist, none is turnkey.** FLUX.2 [klein] 4B (Apache-2.0) for insertion, completion and reference editing; See-through for occlusion-completed part layers (strong, but anime-trained and with a training-data provenance question); our own scripted mesh/weights/rig/clip pipeline compiled to Godot; video models only as motion reference (Experimental, research §2).
4. **Recommended strategy:** data-first, engine-agnostic platform (layer manifest, rig and clip schemas; CLIs with fixed contracts; engine adapters), proven by **small spikes before building** (13 spikes in 4 tiers; S1 is done, S2–S4 need nothing new), on a **layered hybrid rig** (partial skeletal + swaps + baked secondary motion), measured on a **5-character benchmark suite** in at least two styles.
5. **Main constraints:** 16 GB RAM and 85 GB free disk (more than the 12 GB GPU); licence traps (all FLUX.1-dev derivatives, InsightFace, RMBG-2.0 and others excluded); no technical-artist role; lifecycle friction when tools fail (OQ-048).
6. **Effort:** about 45–65 Board-operator days to an end-to-end validated character and a reusable platform, re-estimated after each milestone; local compute only; one likely hardware purchase (RAM); Spine only if justified later.

## Capability status by label

| Label | Items |
|---|---|
| **Verified** | text-to-image (SDXL, FLUX schnell); img2img; masked repaint/removal with exact outside-mask restore; masks, compose, diff, trim; engine import and frame capture; vision review of stills; provenance records; ComfyUI core node inventory |
| **Experimental** (spike planned) | object insertion (S5, S6); character consistency (S6, LoRA); matting (S7); layer decomposition and occlusion completion (S8, S9); scripted Godot rig (S2); auto mesh and weights (S10); preset-based clip authoring (S4); render capture with alpha (S3); QA gate (S11); video motion reference (S12); dual Godot/Spine export (S13) |
| **Proposed** | Studio Art Platform architecture, schemas, CLIs, engine adapters, project profiles, R&D environment, benchmark suite, gates B–D/F–G, `technical-artist`/`animator` roles |
| **Unknown** | whether occlusion completion is authoritative enough for unattended use; whether automatic weights reach commercial quality; whether a vision model can judge animation appeal; See-through generalisation to painterly and pixel styles; Windows/RAM behaviour of 20B models; Spine runtime terms for agent-generated data |

## Required Board decisions

| # | Decision | Recommendation |
|---|---|---|
| D1 | Approve the approach: Claude Code runs M0–M2 research and spikes for the Board; `director` reviews; no new agent yet | Approve |
| D2 | Approve a separate **R&D ComfyUI** environment and the tier-1 install list for spikes only (FLUX.2 klein 4B + text encoder, Acly inpaint nodes + Fooocus patch, BiRefNet/ToonOut), each with the registry security review; production ComfyUI unchanged | Approve tier 1 now; tiers 2–3 after M1 results |
| D3 | Hardware: RAM 16 → 64 GB and a storage plan for models (another drive or cleanup) | Approve RAM before S12/Qwen 20B; decide storage before tier 2 |
| D4 | **Training-data provenance policy** for third-party models (See-through trained on scraped Live2D models; SDXL on LAION): allowed for internal tools with assets reviewed, or excluded | Board policy needed before S8 |
| D5 | Licence policy: commercial-only weights; SAM 3 custom licence → legal check, else SAM 2.1; no FLUX.1-dev derivatives, InsightFace, RMBG-2.0 | Approve |
| D6 | Spine: no purchase now; revisit after S2/S10 with a legal reading of the runtime terms | Approve deferral |
| D7 | Roles: propose `technical-artist` (and maybe `animator`) only after M2 evidence, with scope, runtime, model, permissions and cost | Approve deferral |
| D8 | Benchmark suite B1–B5 (original subjects; Scrivener = B2) and quality gates A–G as defined | Approve |
| D9 | Deckbound: SOU-64 stays parked as B2; SOU-77 waits for M3; other pilot Tasks continue on current tools; G8 of Art Production v2 records SOU-64 as a tool capability failure | Approve |

## What this package does not do
It installs nothing, grants no permission, creates no agent, buys nothing, and changes no approved Deckbound decision. Each later step returns to the Board with its evidence.

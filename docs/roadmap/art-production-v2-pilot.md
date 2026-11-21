# Art Production v2 — Phase 1 Pilot and Exit Gate (G8)

- **Status:** `PROPOSED` (2026-11-22). The release gates G1–G7 are in [runtime-management.md §1.0](../operations/runtime-management.md#10-comfyui-draft-script-and-art-ops-d1-2026-11-22); this document selects the pilot project, lists what must be true before its first Task is released, and defines **G8, the Phase 1 exit gate**.
- **Owner:** Board Operator (release, decisions, evidence); `project-manager` keeps the metrics sheet once the pilot runs.
- **Scope:** Board-assisted pilot ([domain/art/README.md](../../knowledge/departments/game/domain/art/README.md)). No new role, permission, tool or status.

## 1. Pilot project: Deckbound
| Candidate | Fit | Reason |
|---|---|---|
| **Deckbound** (Godot) | **Selected (proposed)** | Art bible, pipeline, ComfyUI workflow, asset specs and registry exist (`docs/art/`, `design/assets/`); its M1 plan already contains the art slice Tasks SOU-64 to SOU-69 and the swap-in SOU-61; the Board's 2026-11-22 decision on AI-made final art names its pipeline |
| Lamplight Vigil (Phaser) | Not suitable | Its `AGENTS.md` allows only original or CC0 assets and forbids "AI-generated art with unclear terms"; generated art cannot enter it without a Board change to that rule |

## 2. Readiness: what must be true before the first pilot Task is released
Checked 2026-11-22 against the live company, the Deckbound repository (`main` 1c86e25) and Company OS `main` (a5c7e91).

| # | Item | State | Unblocks with | Owner |
|---|---|---|---|---|
| R1 | Release gates G1–G7(a) | G1 passed (49/49 on a5c7e91); G2 in PR #88; G3–G7 wait for its merge | Merge PR #88, then run G3–G7(a) in order | Board |
| R2 | `game-artist` registered for Deckbound | The Company OS project registry entry has **no `agents` list** and a stale status comment, while Deckbound is a live Paperclip project with an M1 plan | This branch adds the `agents` list (same roles as Lamplight Vigil); the Board confirms the list when merging | Board |
| R3 | Pipeline matches the 2026-11-22 decision | Deckbound `ART-PIPELINE.md` on `main` still requires a human Krita paintover; deckbound **PR #20** (AI-made final art, updates ART-PIPELINE, COMFYUI-WORKFLOW, ART-BIBLE) is open and mergeable | Review and merge deckbound PR #20 | Board |
| R4 | Explicit asset licensing rule | Deckbound's `AGENTS.md` states none (asset-production precondition: without one, production art does not start). PR #20 still says "model licences are still to be verified" | Board states the rule; a small Deckbound Task commits it to `AGENTS.md`. Proposed text: "Allowed: original work; output of the registered checkpoints `sd-xl-base-1-0` (CreativeML Open RAIL++-M, use restrictions apply) and `flux1-schnell-fp8` (Apache-2.0) made through comfy-draft; PixelFX effects only with Board approval for this project. Not allowed: third-party art, fonts or references fed to a generator. Provenance recorded per asset in its spec." The licences are verified in PR #88 | Board, then `game-artist` Task |
| R5 | Evidence folder | Deckbound Tasks use `assets/slice/review/`, not the v2 default `art_src/review/<TASK-KEY>/` | Record `assets/slice/review/` as Deckbound's review-evidence folder in its `AGENTS.md` (same Task as R4); art-ops can already write there | `game-artist` Task |
| R6 | Pilot Task descriptions in v2 form | SOU-64 to SOU-69 predate v2: no lane, target size and background, reference traits, rubric or `qa` review stage; reviewer is `director` only | The Board rewrites each description from [asset-task-template.md](../../knowledge/departments/game/domain/art/asset-task-template.md) (read with `GET /issues/{id}`, then PATCH), keeps the `director` stage and adds a `qa` stage | Board |
| R7 | Ownership conflicts | **SOU-61** (swap-in) writes `scenes/combat/` and `scenes/card/` but is assigned to `game-artist`, who must not change scenes (interim technical-art split); **SOU-69** (combat UI composition) has no `ui-designer` part | Reassign SOU-61 to `gameplay-programmer` as the integration Task; decide whether SOU-69 stays decorative UI art (`game-artist`) with a separate `ui-designer` layout Task | Board |
| R8 | Direction authority | Deckbound's art bible says `director` approves direction (pipeline §6); the company default is `game-designer`. The project rule wins (game-rules §6) | Use `director` as the L2 review stage for Deckbound and say so in SOU-64 | Board |

The first Task is released only after R1 to R8 are done; it is G7(b).

## 3. Pilot set (Deckbound M1 art slice)
| Task | Content | Lane (proposed) | Covers |
|---|---|---|---|
| SOU-64 | The Scrivener (main character, parts atlas for Skeleton2D) | **L2** direction (handoff A: `director` review stage decides), then L1 production | Character, L2 decision |
| SOU-65 | Two common enemies | L1 | Character family consistency |
| SOU-66 | Card illustration sample | L1 | Illustration |
| SOU-67 | Bind-slot icon states and fray VFX | L1 (icons) + VFX frames | Icon family, VFX or animation |
| SOU-68 | Combat background, flooded hall | L1 | Environment |
| SOU-69 | Combat UI composition | L1 game UI (see R7) | Game UI |
| SOU-61 | Swap-in to the game | Integration (`gameplay-programmer`, see R7) | Integration, in-engine evidence |
| any | First `changes_requested` fix or extra variant | L0 | Fix or variant |

Order: SOU-66 first, as G7(b) (a single L1 asset: G7 asks for an L0 or L1 Task); then SOU-64 (the L2 decision, which SOU-65 follows for family consistency); then SOU-65, SOU-67, SOU-68 and SOU-69 one at a time (WIP 1 per agent); SOU-61 last.

## 4. Evidence per gate (log kept on the pilot planning issue)
| Gate | Evidence recorded |
|---|---|
| G1 | Repository commit tested; full test output (count, skips) |
| G2 | Registry entries merged (PR, commit); each entry's security review line; provenance (checkpoint SHA256 equals the official file) |
| G3 | Copy commands run; time; ComfyUI process restarted |
| G4 | SHA256 of each wrapper in the repository and installed; ComfyUI commit and `git status`; checkpoint SHA256s; Pillow and NumPy versions — all equal to the registry |
| G5 | `check-agent-drift.py` output; the effective `game-artist`, `ui-designer`, `gameplay-programmer` and `qa-engineer` allowlists as read back from Paperclip |
| G6 | Sync dry run, sync, read-back dry run (all `current`), drift check output |
| G7(a) | Installed art-ops: successful operations (`info`, `resize --filter nearest`, `contact --bg`) and refused ones (`..` path, junction, `.git`); **one text-to-image generation with each checkpoint** (`--model sdxl`, `--model flux`), its PNG, workflow and provenance JSON, and the ComfyUI log showing `--offline` |
| G7(b) | SOU-66 end to end: plan comment with lane, committed evidence in `assets/slice/review/`, independent `qa` verdict with the rubric, `director` review, Board merge |

## 5. G8 — Phase 1 exit gate
**Passes when** the pilot set of §3 has run (accepted or stopped), the metrics below are recorded for **every** Task including failed, abandoned and reworked ones, and the Board has accepted the report and decided the Phase 2 order.

Metrics per Task (one row each, kept by `project-manager` from Paperclip and the PRs):

| Metric | How it is measured |
|---|---|
| Visual quality | Rubric scores (0–2 per category) from the `qa` and `director` verdicts, with their observations; hard-gate failures listed |
| First-pass acceptance | Accepted at the first review without `changes_requested`: yes or no |
| Refinement rounds | Self-critique rounds reported in the handoff, plus review rounds (`changes_requested` count) |
| Cost | Number of runs and their total duration; model spend where Paperclip reports it; GPU minutes from the provenance files |
| Human intervention | Every Board or human action beyond release and approval: description fixes, manual art edits, decisions asked, unblocks |
| Integration rework | Art changes requested by `gameplay-programmer` during SOU-61, and in-engine defects found by `qa` |
| Tool capability failures | Every defect the approved tools could not fix (for example a region that needed inpainting, a missing composite, a missing pixel diff, a reference that could not be used), with the Phase 2 workstream it points to |
| Outcome | Accepted, accepted with exception, stopped (reason), cancelled |

**Report to the Board:** the table, totals and medians, the failure list, and a tally of tool capability failures by Phase 2 workstream ([art-production-v2-phase2.md](art-production-v2-phase2.md)). The tally orders Phase 2. A hard-gate regression, or a pilot where most Tasks needed human art edits, fails G8: the Board then decides between more Phase 1 work and a smaller Phase 2 start.

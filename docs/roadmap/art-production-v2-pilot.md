# Art Production v2 — Phase 1 Pilot and Exit Gate (G8)

- **Status:** `PROPOSED` (2026-11-22; revised after the PR #89 review). Planning only: this document changes no tool, permission, agent or Paperclip state. The release gates G1–G7 are in [runtime-management.md §1.0](../operations/runtime-management.md#10-comfyui-draft-script-and-art-ops-d1-2026-11-22); G1–G7(a) have passed (§8).
- **What it defines:** the pilot project (§1), readiness items (§2), the two-stage acceptance model (§3), the pilot set with its dependencies, budgets and stop conditions (§4), the release checklist (§5), metric sources (§6) and **G8, the Phase 1 exit gate** (§7).
- **Owner:** Board Operator: decisions, release, evidence and the metrics sheet (agents cannot read other issues or run logs, G-8, so no agent compiles the metrics).
- **Scope:** Board-assisted pilot ([domain/art/README.md](../../knowledge/departments/game/domain/art/README.md)). No new role, permission, tool or status.

## 1. Pilot project: Deckbound
| Candidate | Fit | Reason |
|---|---|---|
| **Deckbound** (Godot) | **Selected (proposed)** | Art bible, pipeline, ComfyUI workflow, asset specs and registry exist (`docs/art/`, `design/assets/`); its M1 plan already contains the art slice Tasks SOU-64 to SOU-69 and the swap-in SOU-61; the Board's 2026-11-22 decision on AI-made final art names its pipeline |
| Lamplight Vigil (Phaser) | Not suitable | Its `AGENTS.md` allows only original or CC0 assets and forbids "AI-generated art with unclear terms"; generated art cannot enter it without a Board change to that rule |

## 2. Readiness items
Checked 2026-11-22 against the live company, the Deckbound repository (`main` 1c86e25) and Company OS `main` (c998f32, PR #88 merged).

| # | Item | State | Unblocks with | Owner |
|---|---|---|---|---|
| R1 | Release gates G1–G7(a) | **Done**: passed on c998f32 (§8) | — | Board |
| R2 | `game-artist` registered for Deckbound | The project registry entry had no `agents` list | This PR adds it (same roles as Lamplight Vigil); the Board confirms it by merging | Board |
| R3 | Pipeline matches the 2026-11-22 decision | Deckbound `ART-PIPELINE.md` on `main` still requires a human Krita paintover; deckbound **PR #20** fixes that and is open | Review and merge deckbound PR #20 | Board |
| R4 | Explicit asset licensing rule | Deckbound's `AGENTS.md` states none; without one, production art does not start (asset-production precondition) | Board states the rule; a Deckbound Task commits it. Proposed text: "Allowed: original work; output of the registered checkpoints `sd-xl-base-1-0` (CreativeML Open RAIL++-M, use restrictions apply) and `flux1-schnell-fp8` (Apache-2.0) made through comfy-draft; PixelFX only with Board approval for this project. Not allowed: third-party art, fonts or references fed to a generator. Provenance recorded per asset in its spec." | Board, then a `game-artist` Task |
| R5 | Evidence folder and direction record | Deckbound uses `assets/slice/review/`; it names no direction-record file | Same Deckbound Task as R4: record `assets/slice/review/` as the review-evidence folder and `docs/art/directions/` as the direction-record folder in its `AGENTS.md` | `game-artist` Task |
| R6 | Pilot Task descriptions in v2 form | SOU-64 to SOU-69 predate v2 (no lane, target size and background, reference traits, rubric, budgets or `qa` stage) | The Board rewrites each from [asset-task-template.md](../../knowledge/departments/game/domain/art/asset-task-template.md) with the budgets of §4.3 (read with `GET /issues/{id}`, then PATCH) | Board |
| R7 | Ownership conflicts | **SOU-61** writes `scenes/combat/` and `scenes/card/` but is assigned to `game-artist`, who must not change scenes; **SOU-69** has no `ui-designer` part | Reassign SOU-61 to `gameplay-programmer`; decide whether SOU-69 stays decorative UI art (`game-artist`) with a separate `ui-designer` layout Task | Board |
| R8 | Direction authority | Deckbound's art bible names `director` as art-direction approver (pipeline §6); the company default is `game-designer`; a project rule wins (game-rules §6) | **Pending Board decision.** When given, record it here with its date and the Board's words, and in SOU-64a's description. Not recorded until then | Board |
| R9 | Preview before art approval | No approved way to see a new asset in the engine before integration: `game-artist`'s Godot rules render only the project's main scene, scenes are outside its write set, and art-ops cannot composite onto a background image yet (2B) | Default: the two-stage acceptance of §3 (in-context checks deferred to integration, never waived). Optional, separate Board decision outside this PR: a Deckbound preview fixture (a `gameplay-programmer` Task) plus one exact allowlist rule | Board |
| R10 | L2 split and blocker graph | SOU-64 mixes the L2 direction decision with production; blocker relations do not match §4.2 | Create SOU-64a (direction Task) and set the relations of §4.2 in Paperclip | Board |
| R11 | Planned L0 sample | None exists | Create the L0 Task of §4.4 in `backlog` | Board |

The first pilot Task is released only when R1–R11 are done and the checklist of §5 passes; that release is G7(b).

## 3. Acceptance model: art-ready, integration-ready, verified
The art Task merges before the asset exists in the game, and the integration Task needs the merged asset. The company-wide contract that breaks this circle, with the hard gates of each stage, is in [quality-rubric.md, acceptance stages](../../knowledge/departments/game/domain/art/quality-rubric.md#acceptance-stages); the art and integration Task templates and the handoff and verdict formats carry it, so every reviewer receives it in the Task description. For Deckbound the stages map onto its registry statuses:

| Stage | Deckbound registry status | Reached by |
|---|---|---|
| Art-ready | `approved` | Art Task (SOU-64 to SOU-69, L0) approved and merged |
| Integration-ready | `integrated` | SOU-61 (or the Board's smaller pilot integration Task) approved and merged |
| Verified | `verified` | `qa`'s verdict on that integration Task names the asset as verified |

Every pilot art Task names its integration Task (SOU-61, or the replacement the Board creates); in-context checks are deferred only to it and stay `UNVERIFIED` until it validates them. **An asset counts as production-accepted in G8 only when it is `verified`.** A failed deferred check becomes an L0 fix Task, counted once as integration rework (§4.4).

## 4. Pilot set
### 4.1 Tasks
| Task | Content | Lane | Assignee | Reviewers (Paperclip stages) |
|---|---|---|---|---|
| **SOU-64a** (new) | The Scrivener: direction sheet (3–4 directions at target size and in a representative composition) and direction record `docs/art/directions/char_scrivener.md` | **L2** (handoff A) | `game-artist` | `director` (decides, R8), `qa`, then Board approval |
| SOU-64 | The Scrivener: production in the chosen direction (full figure and Skeleton2D parts atlas) | L1 | `game-artist` | `qa`, `director`, Board |
| SOU-65 | Two common enemies | L1 | `game-artist` | `qa`, `director`, Board |
| SOU-66 | Card illustration sample | L1 | `game-artist` | `qa`, `director`, Board |
| SOU-67 | Bind-slot icon states and fray VFX frames | L1 | `game-artist` | `qa`, `director`, Board |
| SOU-68 | Combat background, flooded hall | L1 | `game-artist` | `qa`, `director`, Board |
| SOU-69 | Combat UI composition | L1 game UI (R7) | per R7 | `qa`, `director`, Board |
| **L0** (new, §4.4) | One planned variant of an accepted asset | L0 | `game-artist` | `qa`, Board |
| SOU-61 | Swap-in to the game: integration and every deferred check | Integration | `gameplay-programmer` (R7) | `qa`, `game-artist` (visual result), Board |

### 4.2 Blocker relations (Paperclip, not prose)
| Task | Blocked by |
|---|---|
| SOU-64 | SOU-64a |
| SOU-65 | SOU-64a (the enemies follow the main character's chosen direction) |
| SOU-69 | SOU-68 (the UI is composed against the chosen background) |
| L0 sample | SOU-65 |
| SOU-61 | Its existing blockers (SOU-52, SOU-54, SOU-56, SOU-64, SOU-65, SOU-68) plus SOU-66, SOU-67 and SOU-69 when their assets are in its scope |
SOU-66, SOU-67 and SOU-68 have no art blockers. A cancelled Task has its relations moved to its replacement first (task-contract §6). **Schedule note:** SOU-61 also waits for the M1 gameplay chain (SOU-52, SOU-54), so the integrated slice that G8 PASS requires depends on M1 progress; the Board may split a smaller pilot integration Task that is not blocked by SOU-54, if it wants G8 earlier.

Release order (WIP 1 per agent): SOU-66 (G7(b)) → SOU-64a → SOU-68 → SOU-64 → SOU-65 → SOU-67 → SOU-69 → L0 → SOU-61.

### 4.3 Budgets and stop conditions
Written into each Task description (R6). Defaults; the Board may set others per Task.

| Lane | Generated images (comfy-draft) | Critique rounds | Author runs (excluding review-fix runs) | Agent run time | Review rounds |
|---|---|---|---|---|---|
| L0 | 8 | 1 | 1 | 30 min | 2 |
| L1 | 32 | 2 | 3 | 2 h | 2 |
| L2 direction | 48 | 1 (on the sheet) | 3 | 2 h | 2 |
| Integration | — | — | 3 | 3 h | 2 |

Cost is measured as agent run time plus GPU time (§6); a money cap is `UNAVAILABLE` until Paperclip reports spend for these runs.

**Stop conditions** (the author stops and reports; the Board decides the next step):
1. Any budget reached: hand off with the remaining defects listed, or `blocked` (type `decision`, owner Board) when a hard gate still fails.
2. A defect the approved tools cannot fix: record it as a **tool capability failure** with the Phase 2 workstream it points to, and stop that path.
3. A third `changes_requested` on the same Task: the Board continues with a new budget, reassigns or cancels.
4. The same defect after two fix attempts: a tool capability failure (2).
5. Two tool errors in a row (ComfyUI crash, timeout): `blocked` (type `environment`, owner Board).
6. A running ComfyUI server whose `argv` lacks `--offline`: stop; the Board restarts it through the wrapper (OQ-049 item 8).

### 4.4 L0 sample and counting rework once
The L0 sample is a **planned** Task, independent of review outcomes: after SOU-65 is accepted, one additional state or variant of an accepted enemy from its spec (for example a hit-state frame), created by the Board in `backlog`. Counting rules:
- A `changes_requested` fix is a review round of its own Task, never an L0 sample.
- A failed deferred check found during SOU-61 becomes an L0 fix Task and is counted once, as **integration rework** of the original art Task; its runs and time are added to that Task's cost, not to the L0 sample.

## 5. Pilot release checklist (before G7(b), and repeated for each later pilot release)
1. R1–R11 done; R8 recorded with the Board's words.
2. The Task is in `backlog`, assigned to the intended agent, and its description passes the template's rules: one outcome, exactly one `## Acceptance criteria` and one `## Write set`, paths in backticks, a readable `## Read set`, the lane, budgets and stop conditions, the deferred checks (§3) for art Tasks.
3. Write set: does not overlap any unmerged Deckbound Task (the `release` guard checks this); art Tasks include the evidence folder; no `scenes/` or `scripts/` for `game-artist`.
4. Blocker relations exist in Paperclip as in §4.2 (`pc.py show <KEY>` lists them); all are `done` for this Task.
5. Execution policy: every named reviewer is a review stage (`qa`, plus `director` or `game-artist` as listed), then the Board's approval stage.
6. The assignee has no other `in_progress` Task (WIP 1).
7. The running ComfyUI server, if any, has `--listen 127.0.0.1` and `--offline` in `/system_stats` `argv`; the installed wrappers still match G4's hashes.
8. Release only with `pc.py release <KEY>` (WIP, read-only-assignee and write-set guards). No UI release, no agent `create_task`, no `Auto-release` line during the pilot.

## 6. Metrics: source and owner
All collected by the **Board** (with `pc.py show`, `pc.py log`, GitHub PRs and local files); agents cannot read other issues or run logs. A value that cannot be obtained is written `UNAVAILABLE` with the reason, never estimated.

| Metric | Source | If missing |
|---|---|---|
| Visual quality | Rubric scores and observations in the `qa` and `director` verdict comments (Paperclip) | `UNAVAILABLE` if a verdict has no scores; the review is then incomplete |
| Hard-gate results | Same verdicts; art-ready and integration-ready stages | — |
| First-pass acceptance | Paperclip stage history: no `changes_requested` before approval | — |
| Refinement rounds | Critique rounds in the art handoff comment; review rounds from the stage history | Handoff without rounds: `UNAVAILABLE` |
| Generated images | Count of PNGs in `~/game-studio-workspace/staging/art/<asset_id>/` and its provenance files | — |
| Agent run time | Paperclip run records of the Task (`pc.py show`, run start and end) | — |
| GPU time | `Prompt executed in N seconds` lines in `staging/art/comfyui-server.log`, attributed to the Task by time; comfy-draft's provenance has no duration | `UNAVAILABLE` when attribution is ambiguous (overlapping runs) |
| Model spend | Paperclip cost data if it reports it for the run | `UNAVAILABLE` (expected for now) |
| Human intervention | The Board's own log of actions beyond release and approval: description fixes, manual art edits, decisions, unblocks | — |
| Integration rework | SOU-61 comments and its L0 fix Tasks (§4.4) | — |
| Tool capability failures | Art handoffs, `qa` findings and stop condition 2, classified by the Board by Phase 2 workstream | — |
| Outcome | Final Task state plus the asset's registry status (`verified` or not) | — |

## 7. G8 — Phase 1 exit gate
G8 is **NOT EVALUATED** until every Task of §4.1 has a final outcome and every row of §6 is filled for every Task, including failed and abandoned ones (a value may be `UNAVAILABLE` with its reason). Then it has exactly one of three outcomes, decided by the rules below in order.

### 7.1 Counting
- **Direction (L2):** SOU-64a is measured on its own: direction accepted by its deciding review stage (yes or no), review rounds, budget used. It is not a production asset and is not in the production counts.
- **Production art Tasks:** SOU-64, SOU-65, SOU-66, SOU-67, SOU-68, SOU-69 (six), plus the L0 sample reported separately.
- **Cancelled Tasks:** a Task the Board cancels for a reason outside art production (an M1 scope or schedule change), recorded with that reason, is **excluded** from the denominators and listed. Any other cancellation counts as **stopped** (not art-ready).
- **Human art intervention**, per production art Task: **none**; **guidance** (Board decisions, description fixes, unblocking: not an art edit); **partial** (a human changed pixels of some of the delivered art); **full** (a human produced the art). A Task with partial or full intervention is **human-assisted**: it is reported but **never counted as art-ready** for G8.
- **Art-ready count** = production art Tasks that reached art-ready with no human-assisted art. **Verified** follows §3.

### 7.2 Rules, applied in this order
1. **FAIL** if any of:
   - F1: a hard-gate regression (a merged asset later found to break licence, provenance, originality, technical contract or scope);
   - F2: more than half of the non-excluded production art Tasks are human-assisted;
   - F3: no production art Task reached art-ready.
2. Otherwise **PASS** if all of:
   - P1: a **vertical slice is verified**: the Scrivener (SOU-64), at least one common enemy (SOU-65) and the combat background (SOU-68), through SOU-61 or the Board's pilot integration Task, with `qa`'s verdict;
   - P2: the L2 direction (SOU-64a) was accepted by its deciding stage;
   - P3: at least 4 of the 6 production art Tasks (or two thirds of the non-excluded ones, rounded up) are art-ready;
   - P4: the L0 sample is art-ready;
   - P5: no production art Task is human-assisted.
3. Otherwise **CONDITIONAL** if **every** unmet P-condition is explained by at least one **documented tool capability failure** (§4.3 stop condition 2) on the Tasks concerned, each mapped to one Phase 2 workstream.
4. Otherwise (**fallback**) **FAIL**: the shortfall has no tool-capability explanation (process, brief, role, schedule or quality problems).

The rules are exhaustive and exclusive: every evaluated pilot ends in exactly one outcome, and an unsuccessful pilot can never be recorded as PASS.

### 7.3 Consequences
| Outcome | Consequence |
|---|---|
| **PASS** | Phase 1 closes. The Board approves the Phase 2 order from the tool-capability tally, keeping the roadmap's hard dependencies |
| **CONDITIONAL** | Phase 1 stays open. The Board may approve **one remediation capability** for the documented failure, **with only its minimum mandatory dependencies** from the roadmap's hard-dependency table (for example inpainting needs the 2A prerequisites and the 2B `mask`, `compose` and `diff` subset), and nothing else of Phase 2. After it ships through its own gates, the affected pilot Tasks are rerun and G8 is evaluated again. This is not approval of the Phase 2 roadmap |
| **FAIL** | No Phase 2 work. The Board decides the Phase 1 rework (process, templates, role text) and reruns the pilot |

**Report to the Board:** the §6 table per Task, the direction result, totals and medians, every failed, stopped, cancelled or human-assisted Task with its reason, the tally of tool capability failures by Phase 2 workstream ([art-production-v2-phase2.md](art-production-v2-phase2.md)), and the outcome these rules give. The Board confirms the outcome.

## 8. Gate evidence log
Recorded by Claude Code for the Board on 2026-11-22 (times UTC+7). Repository under test: Company OS `main` **c998f32** (merge of PR #88), checked out clean.

| Gate | Result | Evidence |
|---|---|---|
| G1 | **Passed** | `test_art_ops.py` with the embedded Python on a5c7e91 and again on c998f32: `Ran 49 tests`, `OK`, none skipped |
| G2 | **Passed** | PR #88 merged as c998f32 after the Board accepted the four security reviews ("Accept; you merge #88", recorded in commit 5175d77). On c998f32: `validate-registries.py` 0 findings; `test_registry_tools.py` OK; `comfyui`, `comfyui-embedded-python`, `sd-xl-base-1-0`, `flux1-schnell-fp8` all `integrated` with `security review: 2026-11-22 … accepted by the Board`. Provenance: SDXL SHA256 equals stabilityai's file, fp8 FLUX SHA256 equals Comfy-Org/Flux-1-Schnell's file (also checked independently by the PR #88 reviewer). `check-dependencies.py` skips all four (no version command); G4 is their integrity check |
| G3 | **Passed** | 03:17:42 `art-ops.py` and `comfy-draft.py` copied from c998f32 to `$HOME/game-studio-workspace/tools/`. The running ComfyUI (PID 25756, started 02:01 **without** `--offline`) was stopped; afterwards no ComfyUI process and port 8188 closed |
| G4 | **Passed** | SHA256 repository = installed: `art-ops.py` 93d317ea643c10207047e9e15a9c269ad23d3562853e9ecd0ae14900731f5092, `comfy-draft.py` 135b81e9fad459d7e14d30880b68f12d67e6be554a54d7c134ced3da8fb3a13c (working-tree files of the Windows checkout). ComfyUI HEAD a277b5bf213e8a44fa34817b7770b54f86ef4cea (v0.46.0), `git status` clean. Checkpoints recomputed: `sd_xl_base_1.0` 31e35c80fc4829d14f90153f4c74cd59c90b779f6afe05a74cd6120b893f7e5b, `flux1-schnell-fp8` ead426278b49030e9da5df862994f25ce94ab2ee4df38b556ddddb3db093bf72 (both equal the registry). CPython 3.12.10, Pillow 13.0.0, NumPy 2.5.4. `custom_nodes`: only `example_node.py.example` and `websocket_image_save.py`; no `extra_model_paths.yaml` |
| G5 | **Passed** | `check-agent-drift.py`: no adapter or allowlist drift (only the three expected role-text findings, fixed by G6). Effective live allowlists read from Paperclip: Game Artist 34 allowed / 32 disallowed, `acceptEdits`, art and engine rules = PixelFX `list.mjs` and `render.mjs`, the five Godot rules, `comfy-draft.py`, `art-ops.py`; UI Designer and QA Engineer: the five Godot rules each; Gameplay Programmer: Cursor, `--trust --auto-review`, no allowlist (as configured). All equal `agents.json` |
| G6 | **Passed** | From c998f32: dry run `would update` ui-designer, game-artist, gameplay-programmer only; sync `updated` those three; read-back dry run: all ten roles `current` (code-reviewer not imported, as before); `check-agent-drift.py`: 0 drift findings |
| G7(a) | **Passed** | art-ops (installed copy, scratch folder with `.git`): `info`, `resize --filter nearest` 64x64, `contact --bg 40 90 40` succeeded; refused with exit 1 and nothing written: `../x.png`, a junction under `art_src/`, `.git/x.png`. comfy-draft rejected before ComfyUI started: unknown model (exit 2), `--count 9`, `--width 4096`, `--width 500`, `--asset ../g7`. Generation (server started by the wrapper): SDXL seed 7, 512x512, 25 steps, 56 s including start; FLUX seed 7, 512x512, 4 steps, 26 s. Both PNGs: PNG signature, 512x512 RGB, inspected visually (a brass lantern as prompted); workflow and provenance JSON written (model file, licence, seed, steps, size, prompt). Runtime configuration from `/system_stats`: `argv` = `main.py --windows-standalone-build --listen 127.0.0.1 --port 8188 --disable-auto-launch --offline`; ComfyUI 0.46.0, embedded Python 3.12.10. Startup log: custom nodes imported = `websocket_image_save.py` only. Outputs kept in `~/game-studio-workspace/staging/art/g7_smoke/` |
| G7(b) | **Not started** | Blocked by R2–R11 (§2) and the checklist (§5) |
| G8 | Not started | After the pilot set (§4) |

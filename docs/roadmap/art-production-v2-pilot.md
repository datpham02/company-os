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
| R1 | Release gates G1–G7(a) | **Done again 2026-11-22**: reopened after SOU-66 (the first pass did not exercise the agents' permission layer); PR #91 merged and applied live; G1–G7(a) passed on 3807715 with the agent-level permission smoke (§8, second pass). First-pass evidence kept as history | — | Board |
| R2 | `game-artist` registered for Deckbound | **Done 2026-11-22**: the `agents` list (with `game-artist`) merged in Company OS PR #89 (d0c4ddd) | — | Board |
| R3 | Pipeline matches the 2026-11-22 decision | **Done 2026-11-22**: deckbound PR #20 merged (d78f35a, Board approval "Approve; you merge"); the Krita paintover is optional; the local Deckbound clone fast-forwarded so new Task worktrees include it | — | Board |
| R4 | Explicit asset licensing rule | **Done 2026-11-22**: the Board's rule (answer: "Proposed text, in PR #20") is in Deckbound `AGENTS.md` "Assets and licensing" via PR #20 | — | Board |
| R5 | Evidence folder and direction record | **Done 2026-11-22** via PR #20: `assets/slice/review/` (each Task uses its own subfolder, so write sets do not overlap) and `docs/art/directions/` | — | Board |
| R6 | Pilot Task descriptions in v2 form | **Done 2026-11-22**: SOU-61 and SOU-64 to SOU-69 rewritten to the v2 contract (lane, brief, budgets, stop conditions, stage-specific acceptance, review rules) and re-applied after the SOU-66 finding with the working `~/` tool commands and the staging workaround (§8, PR #91). Review stages as in §4.1. Contextual spec checks are classified in §3.1 | — | Board |
| R7 | Ownership conflicts | **SOU-61** writes `scenes/combat/` and `scenes/card/` but is assigned to `game-artist`, who must not change scenes | **Decided by the Board 2026-11-22** (answer: "Keep as UI art"): SOU-61 is reassigned to `gameplay-programmer`; SOU-69 stays `game-artist` decorative UI art (L1), its layout is left to the existing M1 UI work, so the pilot's game-UI coverage is art-side only | Board |
| R8 | Direction authority | Deckbound's art bible names `director` as art-direction approver (pipeline §6); the company default is `game-designer`; a project rule wins (game-rules §6) | **Decided by the Board 2026-11-22** (answer: "Director"): `director` is Deckbound's art-direction authority for L2 decisions and the deciding review stage on SOU-71. Recorded in SOU-71's description (R10) | Board |
| R9 | Preview before art approval | **Resolved through staged acceptance (§3), not by a preview capability.** No in-engine preview exists before integration (`game-artist`'s Godot rules render only the main scene; scenes are outside its write set; art-ops cannot composite onto a background or render text). In-context checks are deferred to a named integration Task and stay `UNVERIFIED` until it validates them (§3.1) | — | Board |
| R10 | L2 split and blocker graph | **Done 2026-11-22**: SOU-71 created (L2 direction for the Scrivener, `director` deciding stage, R8 recorded in its description); Paperclip relations SOU-64 ← SOU-71, SOU-65 ← SOU-71, SOU-69 ← SOU-68; SOU-61 keeps SOU-52, SOU-54, SOU-56, SOU-64, SOU-65, SOU-68 | — | Board |
| R11 | Planned L0 sample | **Done 2026-11-22**: SOU-72 (Board answer: "Attacker hit state"): a 2-frame `hit` reaction in cells 11–12 of `enemy_attacker`'s sheet, frames 1–10 unchanged, the new state documented in the spec. Write set: `assets/slice/enemies/` (the sheet), its evidence folder and `design/assets/specs/enemy_attacker.md`; the asset registry stays out, because slice Tasks never edit it and SOU-61 adds the registry rows. `backlog`, blocked by SOU-65; stages `qa-engineer` → `game-designer` → Board | — | Board |

The first pilot Task is released only when R1–R11 are done and the checklist of §5 passes; that release is G7(b).

## 3. Acceptance model: art-ready, integration-ready, verified
The art Task merges before the asset exists in the game, and the integration Task needs the merged asset. The company-wide contract that breaks this circle, with the hard gates of each stage, is in [quality-rubric.md, acceptance stages](../../knowledge/departments/game/domain/art/quality-rubric.md#acceptance-stages); the art and integration Task templates and the handoff and verdict formats carry it, so every reviewer receives it in the Task description. For Deckbound the stages map onto its registry statuses:

| Stage | Deckbound registry status | Reached by |
|---|---|---|
| Art-ready | `approved` | Art Task (SOU-64 to SOU-69, L0) approved and merged |
| Integration-ready | `integrated` | SOU-61 (or the Board's smaller pilot integration Task) approved and merged |
| Verified | `verified` | `qa`'s verdict on that integration Task names the asset as verified |

Every pilot art Task names its integration Task (SOU-61, or the replacement the Board creates); in-context checks are deferred only to it and stay `UNVERIFIED` until it validates them. **An asset counts as production-accepted in G8 only when it is `verified`.** A failed deferred check becomes an L0 fix Task, counted once as integration rework (§4.4).

### 3.1 Contextual spec checks: static evidence or integration
Classified 2026-11-22 from the Deckbound specs. "Static" means provable with the approved art tools at art-ready; everything else needs a named integration Task and stays `UNVERIFIED` until that Task validates it. An unverifiable check is never marked passed.

| Task | Spec check | Static evidence? | Owner if not static |
|---|---|---|---|
| SOU-66 | Dimensions, naming, size and memory, provenance, originality; subject inside the central 60% and readable at reduced contrast | Yes (`art-ops info`, `grade --contrast` + `resize` previews, review) | — |
| SOU-66 | Readability under the compact-face **text overlay**; text **4.5:1** in the reduced-contrast mockup | **No**: art-ops cannot render text or composite a card frame | **SOU-73** (card integration, `ui-designer`; Board decision 2026-11-22), blocked by SOU-66, SOU-50, SOU-61 |
| SOU-66 | Editable source `art_src/cards/*.kra` | Not producible by agents (no Krita); PR #20 made Krita optional | Spec line replaced: source = generated, reproducible from provenance and the staged workflow JSON (SOU-66 description) |
| SOU-64, SOU-65, SOU-68 | Readability over the real background; scale against the other slice assets; animation timing in context | No | **SOU-61** |
| SOU-67 | Greyscale distinguishability; dimensions, alpha, frame order | Yes (`grade --saturation 0`, `info`) | — |
| SOU-67 | Colour-blind simulation; glyph at about 83 px on a phone; fray VFX over the slot and not hiding the telegraph | No (no colour-blind filter; device and in-scene checks) | **A named integration Task is mandatory before SOU-67 is released.** None exists yet; until the Board names one, SOU-67 is not released |
| SOU-69 | Layout, safe-area shift, 48 dp targets, text 4.5:1 | No: layout and implementation checks, not art | **A named integration Task is mandatory before SOU-69 is released** (the M1 UI implementation). None exists yet; until the Board names one, SOU-69 is not released |

## 4. Pilot set
### 4.1 Tasks
| Task | Content | Lane | Assignee | Reviewers (Paperclip stages) |
|---|---|---|---|---|
| **SOU-71** (L2 direction, plan name SOU-64a) | The Scrivener: direction sheet (3–4 directions at target size and in a representative composition) and direction record `docs/art/directions/char_scrivener.md` | **L2** (handoff A) | `game-artist` | `director` (deciding stage, R8), then `qa`, then Board |
| SOU-64 | The Scrivener: production in the chosen direction (full figure and Skeleton2D parts atlas) | L1 | `game-artist` | `qa`, `director`, Board |
| SOU-65 | Two common enemies | L1 | `game-artist` | `qa`, `director`, Board |
| SOU-66 | Card illustration sample | L1 | `game-artist` | `qa`, `director`, Board |
| SOU-67 | Bind-slot icon states and fray VFX frames | L1 | `game-artist` | `qa`, `director`, Board |
| SOU-68 | Combat background, flooded hall | L1 | `game-artist` | `qa`, `director`, Board |
| SOU-69 | Combat UI composition (decorative UI art; layout in existing M1 UI work) | L1 | `game-artist` (R7) | `qa`, `director`, `ui-designer`, Board |
| **SOU-72** (L0, §4.4) | `enemy_attacker` hit state, 2 frames | L0 | `game-artist` | `qa`, `game-designer`, Board |
| SOU-61 | Swap-in to the game: integration and every check deferred by SOU-64, SOU-65, SOU-68 | Integration | `gameplay-programmer` (R7) | `qa`, `game-artist` (visual result), Board |
| **SOU-73** | Card integration for `card_art_sample`: text-overlay readability and 4.5:1 (checks deferred by SOU-66). Evidence by the existing UI rule (handoff-templates, evidence table): engine frames from the allowed Godot commands stay in the Task Workspace (`.godot/`), listed by path, recaptured by `qa`; not committed, no new permission | Integration (UI) | `ui-designer` | `qa`, `game-artist`, Board |

### 4.2 Blocker relations (Paperclip, not prose)
| Task | Blocked by |
|---|---|
| SOU-64 | SOU-71 |
| SOU-65 | SOU-71 (the enemies follow the main character's chosen direction) |
| SOU-69 | SOU-68 (the UI is composed against the chosen background) |
| SOU-72 (L0 sample) | SOU-65 |
| SOU-61 | SOU-52, SOU-54, SOU-56, SOU-64, SOU-65, SOU-68 (its scope is the Scrivener, the two commons and the background only) |
| SOU-73 | SOU-66, SOU-50, SOU-61 |
SOU-66, SOU-67 and SOU-68 have no art blockers. A cancelled Task has its relations moved to its replacement first (task-contract §6). **Schedule note:** SOU-61 also waits for the M1 gameplay chain (SOU-52, SOU-54), so the integrated slice that G8 PASS requires depends on M1 progress; the Board may split a smaller pilot integration Task that is not blocked by SOU-54, if it wants G8 earlier.

SOU-67 and SOU-69 are released only after the Board names their integration Task (§3.1). Release order (WIP 1 per agent): SOU-66 (G7(b)) → SOU-71 → SOU-68 → SOU-64 → SOU-65 → SOU-67 → SOU-69 → SOU-72 → SOU-61 → SOU-73.

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
| Disposition-repair runs | Paperclip run records whose wake reason is `issue_disposition_repair`, per Task; any such run is also an incident with its cost and counts as human intervention when the Board must unblock (OQ-048 stays open) | — |
| Model spend | Paperclip run record `usageJson.costUsd` (with `costStatus`, `billingType`) for each run of the Task, read with the Paperclip API | `UNAVAILABLE` only when a run has no reported cost |
| Human intervention | The Board's own log of actions beyond release and approval: description fixes, manual art edits, decisions, unblocks | — |
| Integration rework | SOU-61 comments and its L0 fix Tasks (§4.4) | — |
| Tool capability failures | Art handoffs, `qa` findings and stop condition 2, classified by the Board by Phase 2 workstream | — |
| Outcome | Final Task state plus the asset's registry status (`verified` or not) | — |

## 7. G8 — Phase 1 exit gate
G8 is **NOT EVALUATED** until every Task of §4.1 has a final outcome and every row of §6 is filled for every Task, including failed and abandoned ones (a value may be `UNAVAILABLE` with its reason). Then it has exactly one of three outcomes, decided by the rules below in order.

### 7.1 Counting
- **Direction (L2):** SOU-71 is measured on its own: direction accepted by its deciding review stage (yes or no), review rounds, budget used. It is not a production asset and is not in the production counts.
- **Production art Tasks:** SOU-64, SOU-65, SOU-66, SOU-67, SOU-68, SOU-69 (six), plus the L0 sample reported separately.
- **Cancelled Tasks:** a Task the Board cancels for a reason outside art production (an M1 scope or schedule change), recorded with that reason, is **excluded** from the denominators and listed. Any other cancellation counts as **stopped** (not art-ready).
- **Human art intervention**, per production art Task: **none**; **guidance** (Board decisions, description fixes, unblocking: not an art edit); **partial** (a human changed pixels of some of the delivered art); **full** (a human produced the art). A Task with partial or full intervention is **human-assisted**: it is reported but **never counted as art-ready** for G8.
- **Art-ready count** = production art Tasks that reached art-ready with no human-assisted art. **Verified** follows §3.

### 7.2 Rules, applied in this order
1. **FAIL** if any of:
   - F1: a hard-gate regression: a merged asset later found to fail **any** hard gate of its stage (quality-rubric.md: licence and provenance, originality, technical contract, critical readability, evidence, scope), including a deferred check that fails after the asset was counted;
   - F2: more than half of the non-excluded production art Tasks are human-assisted;
   - F3: no production art Task reached art-ready.
2. Otherwise **PASS** if all of:
   - P1: a **vertical slice is verified**: the Scrivener (SOU-64), at least one common enemy (SOU-65) and the combat background (SOU-68), through SOU-61 or the Board's pilot integration Task, with `qa`'s verdict;
   - P2: the L2 direction (SOU-71) was accepted by its deciding stage;
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
**Status 2026-11-22: revalidated (second pass below).** The rows G1–G7(a) below are the **first pass, kept as history**. They passed but did not exercise the agents' permission layer. After PR #91 is merged and applied live, G3–G7(a) are run again and recorded in a new table under this one; G1 and G2 stay valid unless PR #91 changes what they check.

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
| G7(b) | **Started, stopped, not passed** | §5 checklist read back live before release (2026-11-22 20:48): SOU-66 `backlog`, Game Artist; one `## Acceptance criteria`, one `## Write set` (`assets/slice/cards/`, `assets/slice/review/card_art_sample/`, `design/assets/specs/card_art_sample.md`); no blockers; stages QA Engineer → Director → Board; no agent `in_progress`; ComfyUI `argv` with `--listen 127.0.0.1` and `--offline`; installed wrappers = G4 hashes (art-ops 93d317ea…, comfy-draft 135b81e9…). First `pc.py release` refused (a Tools block inside `## Write set`; moved under its own heading in all six art Tasks); second release succeeded 20:49. Runs f625e065, dcd4e9dc, c6ef17b4: the permission layer refused `comfy-draft.py` ("This command requires approval", both `$HOME` and absolute forms) and Read of the staging folder; 0 images, nothing committed; the agent could not set `blocked` (HTTP 422: Paperclip needs a blocker relation, interaction or unblock descriptor). Root cause reproduced: quoted `"$HOME/…"` allow rules never match in Claude Code 2.1.329; fix in PR #91 (unquoted `~/` rules, provenance printed, agent-level permission smoke added to G7(a)). SOU-66 parked in `backlog` by the Board. G7(b) restarts after PR #91 is merged and applied and G3–G7(a) pass again; it passes only after independent `qa`, Director review and Board approval |
| G8 | Not started | After the pilot set (§4) |

### Second pass 2026-11-22 (after PR #91; R1 closed again)
Repository under test: Company OS `main` **3807715** (PR #91 merged as d42cf1b, PR #90 as 3807715), clean checkout.

| Gate | Result | Evidence |
|---|---|---|
| G1 | **Passed** | `test_art_ops.py`: `Ran 49 tests`, `OK`, none skipped |
| G2 | **Passed** | `validate-registries.py`: 0 findings; registry entries unchanged except the UI/UX Pro Max command note |
| Live permissions | **Applied** | `adapterConfig.extraArgs` of `game-artist` (72) and `ui-designer` (70) replaced with build-package's output from 3807715; exactly the five rules changed (quoted `$HOME` → unquoted `~/`), every other field identical on read-back; previous configs kept as a local backup |
| G3 | **Passed** | 04:12:28 `art-ops.py` and `comfy-draft.py` copied from 3807715; ComfyUI PID 6808 stopped, none left |
| G4 | **Passed** | SHA256 identical in repository (3807715) and installation: `art-ops.py` 93d317ea643c10207047e9e15a9c269ad23d3562853e9ecd0ae14900731f5092, `comfy-draft.py` da8043188cc4ea9f3f05bc345b1a3d16a031d1cf757d76ae465c142dd63020bf; ComfyUI a277b5bf213e8a44fa34817b7770b54f86ef4cea (v0.46.0) clean; checkpoints recomputed `sd_xl_base_1.0` 31e35c80fc4829d14f90153f4c74cd59c90b779f6afe05a74cd6120b893f7e5b, `flux1-schnell-fp8` ead426278b49030e9da5df862994f25ce94ab2ee4df38b556ddddb3db093bf72 (= registry); CPython 3.12.10, Pillow 13.0.0, NumPy 2.5.4; `custom_nodes` = the two upstream files |
| G5 | **Passed** | `check-agent-drift.py`: no adapter drift (two role-text findings, fixed by G6) |
| G6 | **Passed** | Dry run `would update` ui-designer, game-artist; sync `updated`; read-back: all nine imported roles `current`; drift 0 |
| G7(a) | **Passed** | **Agent-level, with the live args read back from Paperclip.** `game-artist`: `comfy-draft.py` generated with SDXL (seed 7, 512x512) and FLUX (seed 7, 512x512) and printed provenance; unknown model and `--asset ../g7` rejected by the script; PixelFX `list.mjs` and `render.mjs --out` inside the evidence folder ran; refused: quoted `$HOME` form, `comfy-server.log` as a script, a chained `… && node -e …`. Staging workaround: `art-ops.py info` on both staging PNGs (512x512 RGB), `contact` into the workspace, opened with Read (two brass lanterns as prompted). `ui-designer`: `search.py` ran; refused: the skill's quoted `$HOME` example, another script in the skill folder, `comfy-draft.py`. Server `argv`: `--listen 127.0.0.1 --port 8188 --disable-auto-launch --offline`; nodes imported: `websocket_image_save.py` only. PixelFX output boundary: **policy only** — `render.mjs` writes wherever `--out` points and no filesystem isolation is enforced or claimed (recorded, not passed). **Supplementary run after the PR #92 review (same live args, 2026-11-22):** the checks the first G7(a) pass had covered from the Board shell, and two agent-level negatives that had run only with the package args, were re-run through `game-artist`'s live permission layer: `art-ops.py resize --filter nearest` into `art_src/` and `contact --bg 27 32 38` succeeded; art-ops refused `../x.png` (outside the roots), a junction under `art_src/` (the outside folder stayed empty) and `.git/x.png`; the permission layer refused `comfy-draft.py` without `-I`, a `..` path to it, PixelFX `serve.mjs`, and `ui-designer`'s `search.py`. Agent transcripts of all three G7(a) runs are kept outside the repository (Board workstation, session scratch), not committed (ADR-010) |
| G7(b) | **Started again, not passed** | §5 checklist read back live (SOU-66 `backlog`, Game Artist; one acceptance-criteria and one write-set section with path items only; no blockers; stages QA Engineer → Director → Board; no Task `in_progress`; server `--offline`; wrappers = G4). Re-released with `pc.py release` 2026-11-22; run afcc2c96 generated its first candidate with no permission denial. G7(b) passes only after independent `qa`, Director review and Board approval |

### Incident 2026-11-22: SOU-66 first release
- **Classification:** runtime permission and lifecycle failure, **not an artistic capability failure**. No image was generated, so it says nothing about art quality, and it is not counted in G8's tool-capability tally. It is counted in the pilot's cost and human-intervention records.
- **What happened:** the permission layer refused `comfy-draft.py` (quoted `$HOME` allow rule never matches in Claude Code 2.1.329) and Read of the staging folder; the agent could not enter `blocked` (HTTP 422); Paperclip ran two disposition-repair wakes and escalated to `blocked`; the Board parked SOU-66 in `backlog`.
- **Runs and cost (Paperclip run records):**

| Run | Trigger | Duration | Reported cost (`costUsd`, subscription-included) |
|---|---|---|---|
| f625e065 | release (`issue_status_changed`) | 58.4 s | $0.472 |
| dcd4e9dc | `issue_disposition_repair` | 17.5 s | $0.149 |
| c6ef17b4 | `issue_disposition_repair` | 31.2 s | $0.378 |
| **Total** | | **107.0 s** | **$1.00** (the two repair runs: 48.7 s, $0.53) |

- **Human intervention (Board):** diagnosis, parking SOU-66, PR #91 (allowlist fix, provenance printout, safe-stop rule), SOU-73, scratch lifecycle test SOU-74.
- **Lifecycle finding:** entering `blocked` needs a blocker relation, a pending interaction or approval, or an `unblockDescriptor` owned by the agent itself; verified on scratch issue SOU-74 (422 without, accepted with). Agents cannot send it with their tools (OQ-048).
- **Resume:** after PR #91 is merged and applied and G3–G7(a) pass again, SOU-66 is re-released through `pc.py release` after the §5 checklist; these three runs stay in its cost record.

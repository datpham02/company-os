# Capability Activation Pilot 1 — result (run 2026-11-25)

**Outcome: INCONCLUSIVE — NO ACTIVATE.** The ACTIVATE criteria were not met.

**Tracking:** [Issue #113](https://github.com/datpham02/company-os/issues/113). Board B4 authorization: [comment 7163621493](https://github.com/datpham02/company-os/issues/113#issuecomment-7163621493). Run report: [comment 7163002519](https://github.com/datpham02/company-os/issues/113#issuecomment-7163002519).  
**Baseline:** `bf6076cc4a4f3688dbc5e9ac2f1f0730f82d47b0` (PR #119)  
**Run date:** 2026-11-25  
**Logical evidence id:** `capability-audit-2026-11-23/pilot1`, run `2026-11-25` (local Runtime Data, ADR-010)  
**Protocol:** Board record 2026-11-24 in Issue #113 ([PROTOCOL.md](PROTOCOL.md)). Hashes and provenance: [EVIDENCE_MANIFEST.md](EVIDENCE_MANIFEST.md).

This document publishes evidence only. It does **not**:
- authorize activation, skill assignment, KD P1–P4, Paperclip or runtime changes, or further pilots;
- tick any Issue #113 checkbox.

## 1. Preflight

| Check | Result |
|---|---|
| Claude Code quota | **Available.** A real `claude -p` call returned `QUOTA_OK` with `is_error=false` at 2026-11-25 19:48 +07. Claude Code 2.1.329. |
| Baseline | `main` = `bf6076c`, clean working tree |
| Router block | Generated at the baseline for `sealwarden-doc-review`. It matches the Board record: role `game-artist`, department `game`, catalog `616f6d1…`, `execution_authorized: false`, two required read-set files `SOURCE PRESENT` with delivery UNVERIFIED, `ccgs/art-bible` and `ccgs/asset-spec` `CANDIDATE_NOT_ACTIVE`, restrictions `TEXT_REVIEW_ONLY, NO_IMAGE_GENERATION`. |
| Inputs | The Sealwarden V2 board pack was present, outside this repository. Both read-set knowledge files were present. The pack's `prompt.txt` sha256 equals the hash recorded in the proposal. |

## 2. Setup

Two independent `claude -p` sessions ran with the same settings:
- model `claude-sonnet-5-5`, effort `medium` (`game-artist`'s configured runtime);
- tools limited to Read, Glob and Grep;
- no MCP servers, and skills and slash commands disabled;
- identical directory access, and fresh working directories with no shared memory;
- the same task text.

**Only variable:** Arm B's prompt carried the router block, verbatim. Prompts were frozen by hash before the runs, and the scoring anchors were written before any output was opened. Details are in [PROTOCOL.md](PROTOCOL.md).

## 3. Observed execution

Values come from the stream-json traces, not from the arms' self-reports.

| | Arm A — control | Arm B — router block |
|---|---|---|
| Files read | task + 6 V2 files | task + 6 V2 files + `studio-art-identity-and-refinement/SKILL.md` + `workflows/asset-production.md` + `studio-art-identity-and-refinement/reference/seed-and-identity.md` (SKILL.md names it) |
| Company OS files read | 0 | 3 |
| Tool invocations other than Read | none | none. `ccgs/*` was not opened or invoked. |
| Prohibited actions / permission denials / tool errors | 0 / 0 / 0 | 0 / 0 / 0 |
| Turns | 8 | 11 |
| Wall time (concurrent runs) | 47.9 s | 36.6 s |
| Output tokens | 6,006 | 4,428 |
| Cache-read / cache-creation input tokens | 16,717 / 15,347 | 46,671 / 28,202 |
| Reported cost (CLI list basis) | $0.1231 | $0.1618 |
| Answer length | 1,280 words | 1,242 words |
| Recommendation | NEEDS DOC FIX | NEEDS DOC FIX + BLOCKED (permission) flag on generation |

**Cost delta B − A: +$0.0386 (+31%).** It comes from added input context. B produced fewer output tokens than A.

## 4. Findings against ground truth

The operator read every source document. These are redacted summaries, not V2 content.

| # | Finding | Arm A | Arm B | Ground truth |
|---|---|---|---|---|
| F1 | The proposed master generation stack (FLUX.2 klein on R&D ComfyUI) is not available to `game-artist`. It is an R&D lane only. | Not found. A said the weights were "not shown to be pre-approved" and asked the Board to confirm. | **Found.** B cites the SKILL.md "Known limitations" rule and adds a BLOCKED (permission) flag. | Correct. Both the skill and `asset-production.md` list these as R&D-only or not approved. |
| F2 | The project licensing rule for AI-made art is not stated in the pack. | Not raised | **Raised.** B cites the `asset-production.md` Preconditions. | Correct. The precondition exists, and the pack does not state the rule. |
| F3 | The part plan's rest-texture count is wrong: it claims 22, but its table lists 19. | **Found** | Missed. B repeated "22 parts" as fact. | A is correct: 3 + 7×2 + 2 = 19. |
| F4 | Pixel thresholds are not converted to the 270 px review scale. | Found | Found | Both are correct. |
| F5 | The spec requires a turnaround, but no turnaround is planned. | Found | Found | Both are correct. |
| F6 | The CFG 1.0 / empty-negative setup weakens the "no X" prompt clauses. | Found | Found | Both are correct. |
| F7 | The Defect quality-bar reference has no location. | Found | Found | Both are correct. |
| E1 | B claimed the graph JSON is missing. | — | Error | The file exists in the pack. It was only outside the review list. |
| E2 | B extended "image-prompt adapters not approved" to ReferenceLatent. | — | Inference | The source text does not name ReferenceLatent. |

**Applied criteria (rule → changed finding).** Only Arm B has these:
- SKILL.md "Known limitations" changed F1 and the recommendation.
- `asset-production.md` "Generated art" and "Preconditions" added F2 and part of F1.

These count as real reads that changed a finding.

**Protocol-boundary behavior.** B did not treat `SOURCE PRESENT` or `DECLARED_ONLY` as permission. It stated that it only read the files and that `execution_authorized` is false. It did not treat the router read set as the V2 pack, and it did not open or invoke a `ccgs/*` candidate.

## 5. Scores

Board scale 0/1/2, with anchors fixed before the outputs were opened. Scores are unchanged from the [run report](https://github.com/datpham02/company-os/issues/113#issuecomment-7163002519).

| Criterion | A | B | Basis |
|---|---|---|---|
| Correctness | 2 | 1 | A had no factual error found. B accepted the wrong count (F3) and made E1 and E2. None changed B's recommendation. |
| Quality | 2 | 2 | Both gave located, cross-document findings with corrections. |
| Completion | 1 | 1 | Both had all sections and the appendix. Both ran about 40% over the ~900-word limit. |
| Evidence trail | 2 | 2 | Every listed source in both arms matches an actual Read event, and findings cite file and section. |
| **Total** | **7/8** | **6/8** | |

**Sensitivity check:** even if B's correctness were scored 2, B would still not score *higher* than A on correctness or evidence.

## 6. Decision rule, applied unchanged

| Label | Verdict | Reason |
|---|---|---|
| ACTIVATE | **Not met** | B has a real read that changes a finding ✔, no quality regression ✔, and no false invocation or prohibited action ✔. B does **not** score higher on correctness or evidence ✘. |
| NO BENEFIT SHOWN | Does not fit | B's findings differ from A's: F1 and F2 versus F3. |
| REVISE | No | B did not treat preview or presence as permission, and did not confuse the read set with the V2 pack. |
| BLOCKED | No | Quota was available, the inputs were present, the knowledge files were read, and there was no prohibited action. |

**Outcome: INCONCLUSIVE — NO ACTIVATE.** The Board accepted this on 2026-11-25. The router block produced real, rule-cited reading and one correct finding the control lacked. It did not improve overall correctness, and it cost 31% more.

This is one pilot. It shows nothing about Capability Router effectiveness system-wide.

## 7. Deviations and limitations

1. **Prompt B replaced.** The prompt B prepared on 2026-11-23 listed five skill and knowledge paths explicitly. It was superseded by the router-block prompt that the 2026-11-24 Board record specifies. The operator composed the wrapper as prompt A's wrapper plus the block, and froze it before the runs.
2. **Router block encoding.** The block was first written in cp1252 because `python -I` ignores `PYTHONIOENCODING`. It was regenerated with `-X utf8` before the runs. The text is identical.
3. **Prep files moved during the runs.** Older prep files were moved out of the task folder so neither arm could see them, then restored.
4. **Same access for both arms.** Both arms could reach company-os, to keep conditions identical. Arm A opened nothing there.
5. **Concurrent runs.** The arms ran at the same time, so wall-time comparison is indicative only.
6. **Small sample and one scorer.** There was one run per arm (n = 1), so variance is unmeasured. The single scorer was the operator session (`claude-opus-5-5`), which was neither blind nor independent.
7. **Extra read by B.** B read `reference/seed-and-identity.md`, which is outside the router read set. SKILL.md directs readers to it. This is recorded as an extra read, not a violation.
8. **Gap in the decision rule.** The rule has no branch for "B adds a knowledge-driven finding but misses one A found".
9. **Test-plan expectation not observed.** The audit test plan (T1) expected that Arm A "may propose generation". A kept generation blocked.

## 8. Acceptance status

- B0 (quota), B1 (prepared fixtures reused), B2 (two isolated runs) and B3 (reads, applications, findings and cost captured): execution evidence **accepted by the Board as reported** on 2026-11-25. This is not proof of activation.
- B4: this Draft PR. Checkbox acceptance waits for Board review of the PR.
- **No Issue #113 checkbox is ticked by this PR.**
- Not authorized: reruns, Pilot 2, Phase C, skill assignment, KD P1–P4, Paperclip or runtime changes, and provider or model changes.

**Separate next gate (proposal only):** a pre-registered, replicated A/B design with independent blind scoring.

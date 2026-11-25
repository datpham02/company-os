# Capability Activation Pilot 1.1 — result (run 2026-11-25)

**Outcome:** **ACTIVATE (eligible to propose)** under the pre-registered decision rule. The Board accepted this result with the recorded caveat that blinding failed in practice.

| Item | Value |
|---|---|
| Tracking | [Issue #113](https://github.com/datpham02/company-os/issues/113) |
| Run date | 2026-11-25 |
| Logical evidence id | `capability-audit-2026-11-23/pilot1-1`, run `2026-11-25` (local Runtime Data, ADR-010) |
| Inputs | Byte-identical to Pilot 1 ([../pilot1/](../pilot1/README.md)). Router block generated at `bf6076c`, re-verified on `470914f`. |
| Protocol and freeze | [PROTOCOL.md](PROTOCOL.md) |
| Hashes and provenance | [EVIDENCE_MANIFEST.md](EVIDENCE_MANIFEST.md) |

Board trail on Issue #113:

| Step | Comment |
|---|---|
| Design | [7164331179](https://github.com/datpham02/company-os/issues/113#issuecomment-7164331179) |
| Design approval | [7164551457](https://github.com/datpham02/company-os/issues/113#issuecomment-7164551457) |
| Execution authorization | [7164575773](https://github.com/datpham02/company-os/issues/113#issuecomment-7164575773) |
| Run report | [7164952124](https://github.com/datpham02/company-os/issues/113#issuecomment-7164952124) |
| Result acceptance | [7164982226](https://github.com/datpham02/company-os/issues/113#issuecomment-7164982226) |

This document publishes evidence only. It does **not** authorize any of the following, and it ticks no Issue #113 checkbox:
- Phase C;
- activation;
- skill assignment;
- KD P1–P4;
- Paperclip or runtime changes.

## 1. Preflight and freeze

| Check | Result |
|---|---|
| Quota | `claude -p` returned `QUOTA_OK` for `claude-sonnet-5-5` and `claude-opus-5-5`, 2026-11-25 20:58 +07 |
| Input identity | TASK, prompt A, prompt B and router block match the Pilot 1 sha256 values. The router block regenerated on `main` `470914f` equals the `bf6076c` block. The knowledge files, router script, routing map and catalog are unchanged since `bf6076c`. The V2 pack hashes match Pilot 1. |
| Ground-truth key | **27 items, 4 router-attributable, plus 13 false-claim patterns**. See [PROTOCOL.md §3](PROTOCOL.md#3-ground-truth-key-summary). The operator drafted 14 items. An independent `claude-opus-5-5` session reviewed them **without seeing any output**: it verified 13, marked K05's wording wrong (reworded) and proposed 14 more, of which 13 were added. |
| Frozen before the first run | Key, blind-key copy, seeded order, scoring pipeline and scorer prompt, all by sha256 at 2026-11-25 21:02:28 +07 |

## 2. Execution

- **10 sessions** of `claude-sonnet-5-5`, effort `medium`, ran sequentially from 21:02:33 to 21:09:05 +07.
- **Pair order** came from seed 20261125: AB, BA, BA, AB, AB.
- **All 10 completed.** No disallowed tools, no permission denials, no tool errors, and no stop rule fired.
- **Company OS reads:**
  - Arm B read the router read-set files (`SKILL.md`, `asset-production.md`) in 5/5 runs.
  - Arm B also read `reference/seed-and-identity.md`, which SKILL.md names, in 3/5 runs.
  - Arm A opened no Company OS file in any run.

## 3. Results

Scores come from the blind scorer, a fresh `claude-opus-5-5` session that never had access to the output-to-arm mapping. Evidence trail is scored mechanically from the traces.

| Run | Arm | Correctness | Quality | Completion | Evidence | Primary | Key recall | Router items found | Errors |
|---|---|---|---|---|---|---|---|---|---|
| p1 | A | 1 | 2 | 1 | 2 | 3 | 0.41 | – | 2 |
| p1 | B | 2 | 2 | 1 | 2 | 4 | 0.59 | K02, K03 | 0 |
| p2 | A | 1 | 2 | 1 | 2 | 3 | 0.33 | – | 1 |
| p2 | B | 2 | 2 | 1 | 2 | 4 | 0.67 | K02, K03 | 0 |
| p3 | A | 1 | 2 | 1 | 2 | 3 | 0.44 | – | 2 |
| p3 | B | 2 | 2 | 1 | 2 | 4 | 0.48 | K02, K03 | 0 |
| p4 | A | 1 | 2 | 1 | 2 | 3 | 0.33 | – | 3 |
| p4 | B | 1 | 2 | 1 | 2 | 3 | 0.37 | K02 | 3 |
| p5 | A | 1 | 2 | 1 | 2 | 3 | 0.26 | – | 2 |
| p5 | B | 1 | 2 | 1 | 2 | 3 | 0.44 | K02, K03, K27 | 1 |

| Mean over 5 runs | Arm A | Arm B |
|---|---|---|
| **Primary** (correctness + evidence) | 3.0 | **3.6** (+0.6) |
| Correctness / quality / completion / evidence | 1.0 / 2.0 / 1.0 / 2.0 | 1.6 / 2.0 / 1.0 / 2.0 |
| Key recall (27 items) | 0.356 | **0.511** |
| Key recall excluding router-attributable items | 0.417 | 0.513 |
| Errors per run | 2.0 | **0.8** |
| Errors excluding X02 ("accepts 22 parts", made by both arms) | 1.2 | 0.4 |
| Router-attributable hits | 0/5 | **5/5** |
| K04 (19 vs 22 part count) found | 0/5 | 2/5 |
| Preview treated as permission (X06) / prohibited actions | 0 / 0 | 0 / 0 |
| Cost per run (CLI list basis) | $0.102 | $0.170 (**+$0.068, +67%**) |
| Answer length | 1,253 words | 1,224 words |

Both arms exceeded the ~900-word limit in every run.

**Total Pilot 1.1 spend: $2.74 of the $6 cap.**

| Item | Cost |
|---|---|
| Preflight | $0.033 |
| Key review | $0.515 |
| 10 runs | $1.362 |
| Scorer | $0.828 |

## 4. Pre-registered decision rule, applied unchanged

| Label | Verdict | Basis |
|---|---|---|
| ACTIVATE | **Met** | Primary +0.6 ≥ +0.5 ✔; recall B ≥ A ✔; errors B ≤ A + 0.5 ✔; router-attributable hits 5/5 ≥ 4/5 ✔; no prohibited action or preview-as-permission ✔ |
| REVISE | Not met | B does not regress on recall or errors |
| NO BENEFIT SHOWN | Not met | Primary difference ≥ 0.5, and hits 5/5 |
| BLOCKED | Not met | All 5 pairs completed |

Under the design, **ACTIVATE only makes a Phase C proposal eligible.** It activates nothing.

## 5. Operator checks (outside the scoring)

- **Scorer error calls spot-checked:** two calls were checked against the raw outputs. p1_A wrongly said the prompt omits the stone, apron and seal colours. p4_A's statement about the forbidden-input list contradicts itself. **Both confirmed.**
- **Scorer miss noticed:** p1_B's count arithmetic is internally inconsistent ("2×8 = 16" for 7 paired categories), even though its conclusion of 19 is correct. The scorer did not penalize it. This is recorded, not re-scored.

## 6. Deviations and limitations

1. **Blinding failed in practice.** The scorer guessed the arm correctly for 10/10 outputs, with confidence 0.75–0.9. The design declared blinding partial, but it was effectively absent. B's advantage also holds on two measures that do not depend on router items: recall excluding router items, and errors excluding X02.
2. **The frozen redaction missed a bare `asset-production`** (without `.md`) in two outputs. The rule was not patched after the freeze. Both outputs were already identifiable from `[studio source]` tags.
3. **Evidence and completion did not discriminate.** Evidence trail was 2 and completion was 1 in all 10 runs. The primary difference therefore comes entirely from correctness.
4. **One model scorer.** It is from the same provider family as the arms. There was no human panel, and the Board's optional human spot-check was not used.
5. **n = 5 on one task type.** No claim is made beyond `sealwarden-doc-review` / `game-artist`.
6. **Pilot 1 is not pooled.** Its A-only count finding did not replicate here (A 0/5, B 2/5), which is consistent with n = 1 noise.
7. **Cost overhead is +67% per run.** Pilot 1 showed +31%. The extra cost comes mostly from additional input context.
8. **Key-review session.** It added items and reworded K05 before any run. One added item was overridden to non-router-attributable, because TASK asks both arms for the three lists. One added recommendation item was folded into K01.

## 7. Status

- **Board decisions recorded:** design approved, execution authorized, result accepted.
- **No checkbox ticked.** The Phase C items are separate decisions.
- **Not authorized:** Phase C (its proposal or implementation), skill assignment, KD P1–P4, Paperclip or runtime changes, provider or model changes.

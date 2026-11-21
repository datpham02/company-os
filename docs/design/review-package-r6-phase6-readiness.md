# Review Package R6: Phase 6 readiness assessment

- **Status:** `PROPOSED`, review only. **Update after R5 (2026-11-21):** B1 mostly closed, B2 closed, B5 confirmed as a risk, new blocker B7 (relay override, finding F1), **since closed by PR #64 and a live re-run**; see §5 and [review-package-r5-results.md](review-package-r5-results.md). Written for the Board Operator on 2026-11-21. It neither writes nor authorizes the Phase 6 production proposal (design §11).
- **Question:** what must hold before a Phase 6 production proposal can be written and judged?
- **Inputs:**
  - [review-package.md](review-package.md) §11–§13;
  - [post-Phase 5 assessment](review-package-post-phase5-assessment.md) (roadmap R1–R6, §5 gap matrix, §8 risks);
  - the records of Option B, P0, R1, R2, the redaction probe, ADR-022 and [stage1-gap-analysis.md](../architecture/stage1-gap-analysis.md) (G-13, G-14);
  - code at `main` `90c01b9`.
- **Standing status:**
  - Phase 5 partially accepted;
  - **G-13 OPEN**, G-14 OPEN, V3 not tested;
  - Phase 6 not authorized.

## 1. Verdict

**Not ready.** The review mechanics are built and most of them were verified live: package, staging, review sub-issue, reviewer profile, relay, `--unstage`. A production proposal written today would still rest on:

- **seven §12 criteria** that are only partly live (§3);
- **two open security positions** that decide whether the relay's authority means anything (§4): G-14 and V3;
- **an untested merge step**, the one step the whole design protects.

The blockers are B1–B6 in §5. None of them needs new design work. Each needs either a sandbox run (R5) or a Board decision.

## 2. Roadmap outcomes (R1–R5)

| Item | Outcome | Evidence |
|---|---|---|
| R1 G-13 binding | **Done, live.** The Board chose Option B: review sub-issue, staging challenge, `reviewId` in the verdict, run bound to the lock. The reviewer profile was validated and applied in REV, RPR and OPT. P0 removed Paperclip's write-capable MCP tools from the reviewer | `review-package-option-b-live.md`, `review-package-reviewer-write-isolation.md`, `review-package-r1-*.md` |
| R2 `--unstage` from Paperclip | **Done, live.** An active reviewer run refuses even with `--abandon`. `staging.op` prevents races. `--status` reads from Paperclip (PR #56) | `review-package-r2-results.md` |
| R3 `cancelled` semantics | **Done.** `pc.py show` labels confirmed hand-overs (PR #57). Display only | CHANGELOG |
| A3 (found during R2) | **Done.** Check-phase Paperclip errors are audited refusals (PR #57) | CHANGELOG |
| R4 PR credential | **Decided** (ADR-022): <ul><li>sandboxes: the Board opens the PR, with no token;</li><li>production: one fine-grained token on the Board's account, *All repositories*, an accepted risk.</li></ul> Follow-ups: <ul><li>the redaction probe showed that `env` secrets are **not** redacted in run logs;</li><li>credential rule and deny list applied and verified live (PR #59).</li></ul> | ADR-022, `gh-token-log-redaction-probe.md` |
| R5 §12 live evidence | **Not started.** Needs a throwaway repository and a sandbox run, both Board-approved | — |

## 3. §12 criteria now

"After R1–R4" records what changed since the Phase 5 record. R5 is the run that would close the rest.

| # | Criterion | After R1–R4 | Still missing (R5 test from assessment §5) |
|---|---|---|---|
| 1 | Packager reads only the GitHub API; no git on agent-writable repositories | API source live; "no git" source and offline only | Run under a `git` shim or process trace |
| 2 | §5.3 rules and §5.2 limits refuse | Offline only | A throwaway PR with the bad cases |
| 3 | Immutable per head; `READY` last; stale heads refused | Per head and stale live; `READY` offline | Fault injection between rename and `READY` |
| 4 | Reviewer tools only; reaches only `current/`; write, shell and git fail | Tools exactly Read, Grep and Glob, live (R1 D). Write-capable MCP tools removed and verified by the log check (P0). Write, shell and git **attempts** not tried in Paperclip | Injected instructions in `REVIEW.md` |
| 5 | One review staged at a time | **Live** | — |
| 6 | Relay accepts only §3.4; no duplicates; fallback | Checks 1–4, duplicates, fallback and Option B binding live. Malformed verdict and 4xx offline. Check-phase errors audited (A3) | Bad-schema verdict; a 4xx between check and PATCH |
| 7 | Packager token read-only, selected repositories, never in agent `env` or a log | Not in files or logs; no agent binding. Scope set by the Board | A write attempt expecting 403; a search of logs and the database backup for the prefix |
| 8 | Retention, 2 GB cap, cleanup, logged | Cleanup and audit live (nothing eligible); deletion and cap offline. **`--cleanup` still reads closure from the state file** | A Paperclip-backed closure check first (code change), then a sandbox run |
| 9 | No worktree or branch created, moved or deleted (ADR-006) | Packager and relay live | Before and after snapshots during a full review |
| 10 | G-13 not marked resolved | Holds | — |
| — | Merge by the Board after an approved relay (ADR-009 order) | **Not tested** (the Board closed PR #28) | Merge a sandbox PR in a throwaway repository |

## 4. Security position

- **G-13 (reviewer isolation): open, narrowed.**
  - Option B runs the reviewer on its own sub-issue, not in the author's worktree.
  - P0 removed its Paperclip write tools.
  - The relay checks the run, the tool surface, the log hash and a staging challenge.
  - What remains:
    - the reviewer, the relay's files and the authors run as the same Windows user (G-14);
    - comprehension cannot be proven (assessment §8).
  - The Review Package gives evidence of binding and access. **The Board's approval and merge stay the real gate.**
- **G-14 (`local_trusted`): open.**
  - A request without `Authorization` is the Board.
  - Any same-user process can rewrite the lock, staging, store and audit files. The Cursor authors have a general shell.
  - The authenticated-mode migration (OQ-043, auth migration A1–A5) is planned. D-AUTH-10 to D-AUTH-15 are approved, but implementation is **Pending**.
- **V3 (can an agent reach Board endpoints): not tested.** If yes, the relay's authority is not exclusive: an author could approve its own Task.
- **New since Phase 5:**
  - **Run logs are not redacted** for `env` secrets. Mitigated for Claude agents by a rule and a deny list (verified). Only the rule covers Cursor agents.
  - **ADR-022 accepted risk:** the agents' GitHub token acts as the repository owner, so branch protection probably does not bind it (`UNVERIFIED`). For agent tokens, the merge gate the Review Package feeds is therefore procedural.

## 5. Blockers before a production proposal

A Phase 6 proposal SHOULD NOT be written until each item is closed, or the Board explicitly accepts it as a named risk in that proposal.

| # | Blocker | Closes with | Owner |
|---|---|---|---|
| B1 | §12 criteria 1–4 and 6–9 only partly live; merge untested. **After R5:** 1, 3, 4, 7, 8 and the merge live; 2 representative; 6: override fixed (B7 closed), malformed verdict offline only; 9 open until production | R5 in a throwaway repository: tests 1–4, 6–9 and the merge, or each recorded as Failed | Board approves the repository and the run; Claude runs it |
| B2 | `--cleanup` decides closure from the state file. **Closed:** PR #62, live in R5 test 8 | A code change like R2's (closure from Paperclip, fail closed), then the criterion 8 test | Claude (code, PR); Board approves |
| B3 | V3 untested | A V3 test, with separate authorization; or a written decision to rely on authenticated mode instead | Board |
| B4 | G-14: local Board access and same-user file tampering | Authenticated mode (A5 implementation), or a named accepted risk in the proposal with its consequences for the relay | Board |
| B5 | ADR-022 accepted risk: the agent token may bypass branch protection. **R5: the owner's login bypasses it (confirmed); token level untested** | A throwaway-repository test of an owner fine-grained token against a protected `main`. Then either keep the accepted risk with evidence, or move agents to a separate identity | Board approves the test |
| B6 | Paperclip version coupling | A version pin and a re-check list in the runbook: <ul><li>`decideIssueOwnership`;</li><li>the reassignment cancel;</li><li>run record fields (`logSha256`, `resultJson`);</li><li>MCP tool registration;</li><li>log redaction.</li></ul> | Claude drafts; Board approves |
| B7 (new, R5) | The relay could override a decision the Board makes by hand while it runs (F1). **Closed (narrowed) 2026-11-21:** PR #64 re-checks the issue just before the decision PATCH; R5 test 6b re-run passed live (`OPT-17`). The window between the re-check and the PATCH remains, because Paperclip has no conditional status update; state it in the proposal | — | — |

**Not blockers, but the proposal must state them:**
- comprehension cannot be proven;
- the wake reason may reach the prompt (unverified; Option B does not depend on it);
- whether Paperclip re-verifies `logSha256` on read (unverified; the relay verifies it itself);
- reviewer identity resolved by name at `review-start` (R2 records the resolved id in the lock);
- Cursor-side deny list not configured.

## 6. What the Phase 6 proposal must contain

Design §11 lists: agent, profile, stages, runbook, token. In concrete terms:

1. **Agent:** the `code-reviewer` definition for Soucean, in `config/paperclip/agents.json`, with its profile.
   - The strict profile as validated in R1: `--restricted`, `--tools Read,Grep,Glob`, `--disallowedTools mcp__*`, `--strict-mcp-config`, `dontAsk`, one `--add-dir`.
   - No `env`.
2. **Stages:** which Soucean projects use a review stage with participant `local-board`, and how `in_review` is reached.
3. **Runbook:**
   - the manual sequence `review-pack` → `review-start` → `review-relay` → Board merge;
   - the manual fallback (`approve` / `request-changes`);
   - `--unstage` and `--status`;
   - the retention schedule;
   - the version re-check list (B6);
   - token rotation for the packager token;
   - what to do on each refusal message.
4. **Tokens:**
   - the packager token (read-only, Board-created, Windows Credential Manager);
   - the author token (ADR-022).
5. **Risks:** B3–B5 if accepted rather than closed, plus the items listed under §5.
6. **Rollback:** remove the review stage and the agent. The Board fallback works without the pipeline.

## 7. Recommended order

1. **R5:** Board approves a throwaway repository and the sandbox run. It closes B1 and, in the same repository, B5.
2. **B2:** a small code PR, then its sandbox check inside R5.
3. **B3 and B4:** Board decisions on V3 and on authenticated mode. They can run in parallel with R5.
4. **B6:** runbook draft, with the Phase 6 proposal.
5. **Phase 6 proposal:** written only after 1–4. It needs separate approval.

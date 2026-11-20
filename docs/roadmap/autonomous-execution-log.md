# Autonomous Execution Log

Progress record for the sequential roadmap brief (Steps 0–7). Each step ends with a report to the Board Operator, and the next step starts only on the Board's authorization. Evidence lives in the linked files and commits; this log only summarizes.

## Step 0: current state (2026-11-20)

**Git.**
- `main` at `23d3e97`, the merge of PR #29.
- Work for Step 1 is on branch `fix/review-packager-audit`, created from `main`.
- No commits are made without the Board's approval.

**Roadmap ([phases.md](phases.md)).**
- **Phase 0:** done (experiments recorded in [open-questions.md](open-questions.md); ADR-011 and ADR-012 accepted).
- **Phase 1** (Stage 1 studio):
  - the live company Soucean (`SOU`) runs, with the agents and projects in [config/paperclip/agents.json](../../config/paperclip/agents.json);
  - the gap analysis exists ([stage1-gap-analysis.md](../architecture/stage1-gap-analysis.md), G-1 to G-13).
- **Phases 2–4:** not started.

**Completed since the gap analysis** (merged PRs):

| Work | PR | Gap or question |
|---|---|---|
| Write Set conflict guard in `release` | #21 | Task contract §4 (E1) |
| WIP 1 per agent in `release` and `triage`; paginated issue lists | #22 | G-12 (partly) |
| `release` as the only local start gate | #23 | G-9, G-10 (skill paths only) |
| Reviewer isolation audit | #24 | G-13 (still open), OQ-042 |
| Reviewer experiment on native Windows | #25 | OQ-042 |
| Review package design, decisions, relay authority | #26–#28 | OQ-042 |
| Review packager Phase 1 (`pc.py review-pack`, fixtures only) | #29 | OQ-042 |

**Gap statuses** (from the gap analysis, not yet re-verified):
- G-8: open.
- G-9: open in Paperclip; the skill path is gated.
- G-11: open.
- G-12: worked around.
- G-13: worked around by role rules only; not resolved.

**Open questions:** 25 are Open and 10 Partially verified. The Runtime prerequisites named in the brief (OQ-001, 008, 010, 012–015, 017, 023, 027, 029, 031, 032, 041) are all Open or Partially verified.

**Numbering note.** The brief lists Review Package phases as 2 = GitHub API, 3 = PR/tree/blob verification, 4 = Verdict Relay. [review-package.md §11](../design/review-package.md) defines:
- 2 = strict reviewer tests on a package;
- 3 = GitHub source, which includes PR, tree and blob verification;
- 4 = Paperclip sandbox and Verdict Relay;
- 5 = sandbox end-to-end;
- 6 = production proposal.

Step 3 will follow the design's order, since the design is the approved contract.

## Step 1: audit of the merged review packager (2026-11-20)

**Status:** done locally on `fix/review-packager-audit`. Not committed; waiting for Board review.

**Scope:** `review_pack.py`, `test_review_pack.py`, `pc.py`, `test_pc.py`, `SKILL.md` and `review-package.md`. Checked for security, Windows paths, races, integrity, staging locks, cleanup, the audit log and failure handling.

**Evidence from this machine** (Windows 11, Python 3.12.10; a probe script in a temporary folder, not in the repository):
- A junction planted at `store/<KEY>` made `makedirs` land outside the Review Root. `os.path.islink` is `False` for junctions.
- 8.3 short names are enabled: `LONGFI~1.CS` resolves to `LongFileName.cs`, and an exclusive create of the alias fails with `FileExistsError`.
- `CON .txt` and `con.txt` create ordinary files on Windows 11. They are refused anyway, for older Windows.

| # | Defect | Severity | Fix | Regression tests |
|---|---|---|---|---|
| D1 | The packager followed junctions or symlinks under its roots, so it could write or delete outside them. The containment check compared against the folder that was already redirected | High | `assert_contained` on every store, trash and staging path; `list_files` refuses links inside packages | 6 tests with real NTFS junctions (`_winapi.CreateJunction`) |
| D2 | `CON .txt` (space before the extension) passed the reserved-name rule | Low | Trailing spaces stripped before the check | 1 |
| D3 | Names shaped like 8.3 short names could alias another file and crash the build with a raw `FileExistsError` | Medium | Refused as an explicit path rule | 2 |
| D4 | `verify_package` trusted paths and document names from the manifest, which sits in the package | Medium | Re-validated before use | 2 |
| D5 | Two concurrent builds of one issue removed each other's `.tmp-*` folder | Medium | A per-issue `.build.lock` (`O_EXCL`); a lock older than 60 minutes is taken over and logged; an unreadable lock refuses | 4 |
| D6 | Filesystem errors escaped as raw exceptions with no `refuse` audit entry | Low | The CLI converts `OSError` into a logged refusal | 1 |
| D7 | A half-written audit line crashed `--status` and `--unstage` with a raw `JSONDecodeError` | Low | Refused with the file and line number | 1 |
| D8 | Untrusted Task text came before the instructions in `REVIEW.md` and could pose as them, or close a code span | Medium | Fixed instructions first; Task, PR and path data quoted inside a fence longer than any backtick run | 1 |

- **Check that the tests catch the defects:** 16 of the 18 new tests fail against the previous `review_pack.py` from `main`.
- The other two still pass there:
  - the D4 traversal case was already refused, by accident (file-set mismatch); it is kept as a guard;
  - the D5 lock-release case covers new behaviour.

**Tests:**
- `python -I -W error .claude/skills/paperclip/scripts/test_pc.py`: 153 tests, OK (73 skill tests plus 80 packager tests, of which 18 are new). No warnings.
- `py_compile` passes on all four scripts.

**Files changed:**
- `scripts/review_pack.py`;
- `scripts/test_review_pack.py` (regressions; two assertions updated for the new `REVIEW.md` layout; one cap margin widened because the brief is longer);
- `SKILL.md`;
- `docs/design/review-package.md` §5.3 (two rows and the `REVIEW.md` sentence; status still `PROPOSED`);
- `CHANGELOG.md`;
- this log.

**Remaining risks, unchanged by design:**
- every component runs as the same Windows user, so a determined same-user process can still tamper with the roots between checks (TOCTOU);
- the audit log can be forged by the same user;
- staging is not an OS boundary;
- G-13 stays open.

**Not covered:** real multi-process races (simulated); a full disk; `rmtree` failing on open files outside the cleanup path.

**Next step:** Step 2, Stage 1 validation (G-8, G-9, G-11, G-12, G-13). It waits for Board authorization.

## Step 2: Stage 1 validation (2026-11-20)

**Status:** documentation done on branch `docs/stage1-validation`, created from `fix/review-packager-audit` because this log is not on `main` yet. Not committed. No fixes were implemented.

**Method:** a source audit of the installed Paperclip 2026.1023.0, plus this repository's config and scripts. Paperclip was off and was not started. No live or sandbox experiment was run. Details are in [stage1-gap-analysis.md](../architecture/stage1-gap-analysis.md#step-2-validation-2026-11-20).

| Gap | Finding | Status |
|---|---|---|
| G-8 | Paperclip allows same-company issue and agent reads; the normal agent API path lacks a usable credential (no variables in commands, no read helper or MCP read tool). The separate `local_trusted` path (G-14) is untested from agent runs | Open, cause verified |
| G-9 | MCP `create_task` ignores its own `status` field: always `todo`, assigned to the caller, always exposed | Open, cause verified; skill path mitigated |
| G-11 | Import `replace` still refused; role texts are synced by a script; adapter config, permissions and runtime config have no sync and no drift report | Partially Verified |
| G-12 | `maxConcurrentRuns` queues wakes (answers OQ-041) and limits simultaneous runs, not `in_progress` issues, so WIP still needs its own check; a native 30-second scheduler sweeps stranded and silent work but not `blocked`; cancelled blockers never resolve. New bypass: `pc.py request-changes` has no WIP check | Partially Verified |
| G-13 | Conditions unchanged; the OQ-042 evidence stands; not re-run | Open |
| **G-14 (new)** | `local_trusted` treats any keyless loopback request as the Board and instance admin; Claude profiles allow `Bash(curl *)` (no role uses it). Exploitability from an agent run is untested | **Open (critical)**: source/config verified; exploitability unverified |

**Files:**
- `docs/architecture/stage1-gap-analysis.md`: statuses, a G-14 row, and a Step 2 section;
- `docs/roadmap/open-questions.md`: OQ-041 answered from source, OQ-043 new;
- this log.

**Needs Board decisions:**
- remove `Bash(curl *)` from the Claude profiles (G-14), and how to treat Cursor agents;
- whether to run a separate, non-studio Paperclip instance for sandbox checks (G-14 exploitability, OQ-043, OQ-041, G-9 option 2);
- `maxConcurrentRuns: 1` on non-reviewing agents (G-12);
- narrowing `mcp__Paperclip_projects` to read tools, and the planning workflow (G-9);
- a read-only drift-check tool for agents (G-11, Phase 2).

**Blockers:** every live or sandbox check needs Paperclip running and Board approval. Live configuration changes need Board approval and are applied by hand (G-11).

**Next step:** Board review. Phase 2 tooling has not started.

**Board decision record:** [step2-board-decisions.md](step2-board-decisions.md) (D-STEP2-01 to D-STEP2-06), proposed and approved 2026-11-20 as recommended.

**D-STEP2-01 applied (2026-11-20):** after a fresh database backup, `Bash(curl *)` was removed from the six live Claude agents and from both profiles in `agents.json`; the two Cursor agents are unchanged. Per-agent results and rollback references are in the [execution record](step2-board-decisions.md#6a-execution-record-d-step2-01-2026-11-20). G-14 stays open.

**D-STEP2-02 part (c) done (2026-11-20):** isolated sandbox, no agent runs. `authenticated` mode works on Windows and closes keyless Board access; existing data needs a manual admin and access migration; the scripts need board-token support. Agent runs wait for the sandbox identity decision. Details in the [execution record](step2-board-decisions.md#6b-execution-record-d-step2-02-part-c-2026-11-20) and OQ-043.

**Sandbox agent runs cancelled (2026-11-20):** the Board decided they are not needed. The studio instance was restarted. The Board Operator then removed the sandbox by hand (folder with instance, evidence files and scripts; Windows user, profile and folder rule); a check found nothing left over. G-14 exploitability, OQ-041 and G-9 option 2 stay unverified.

**Authentication migration decisions (2026-11-20):** after the Phase A audit and the Phase A.1 design ([auth-migration-phase-a1.md](../architecture/auth-migration-phase-a1.md)), the Board approved D-AUTH-01 to D-AUTH-05 ([auth-migration-board-decisions.md](auth-migration-board-decisions.md)). Documentation only: no runtime action, no live change. Phase B stays blocked until the isolated verification plan and its results are reviewed.

**Authentication migration Phase A.2 (2026-11-20, planning only):** readiness assessment and verification plan written ([readiness](../architecture/auth-migration-phase-a2-readiness.md), [verification plan](../architecture/auth-migration-verification-plan.md)). Main result, from source: Paperclip's scheduler does not recover the OQ-035 reviewer wake, so the D-AUTH-03 condition is not met and the watchdog decision returns to the Board. Not ready for Phase B (four direct blockers). No runtime action, no live change; OQ-025 and OQ-035 updated with existing evidence.

**Authentication migration Phase A.3 (2026-11-20, planning only):** Board re-decision package prepared ([auth-migration-phase-a3-board-decisions.md](auth-migration-phase-a3-board-decisions.md)): D-AUTH-03R (reviewer wake), D-AUTH-06 (credential storage), D-AUTH-07a/b/c (verification environment, VA cases, VR cases), D-AUTH-08 (documentation commits) and D-AUTH-09 (Board stage freeze). All pending. D-AUTH-03 is marked as under reconsideration; its approval stays in the record. No runtime action, no live change, nothing committed.

**Phase A.3 decisions approved (2026-11-20):** the Board Operator approved all seven as recommended: D-AUTH-03R option A (manual Board sweep), D-AUTH-06 (Windows Credential Manager; residual risks accepted), D-AUTH-07a and 07b (verification environment and VA cases), D-AUTH-07c deferred, D-AUTH-08 (commit the records), D-AUTH-09 (stage freeze). No implementation authorization was given; nothing was created, run or committed.

**D-AUTH-08 carried out (2026-11-20):** the Phase A audit was added as [auth-migration-phase-a-audit.md](../architecture/auth-migration-phase-a-audit.md), and the Phase A to A.3 records were committed in four commits on one branch, with a pull request to `main`. Nothing else was implemented.

**Phase A.4 isolated verification (2026-11-20, D-AUTH-07a and 07b):** a disposable instance (separate home, instance `a4verify`, ports 3300/54349, fresh secrets, no agents) with the live instance stopped. VA-1 to VA-8 passed (VA-1 with different status codes; VA-4c reproduced the duplicate-participant drop); VA-9 is blocked because Paperclip has no supported restore. Sandbox deleted; live instance restarted unchanged. Record: [auth-migration-phase-a4-verification.md](../architecture/auth-migration-phase-a4-verification.md). Committed in PR #42; pending Board review.

**Phase A.4 documentation reconciliation (2026-11-20):** the A.4 report was reviewed against its evidence and the A.2 baseline.
- **Wording:** claim token vs Board API token, the dual-admin rollback state, expiry not tested, backup not proof of recoverability.
- **Added:** security findings SF-1 to SF-6, a per-criterion E1 to E12 table using A.2's exact acceptance wording, and six Board decisions.
- **Statuses:** E2, E3, E4 and E10 met. E5, E6, E7 and E9 have evidence that meets the condition and await Board review. E1 is unclear. E8, E11 and E12 are not met.

No runtime action. Documentation committed in PR #42. Status: READY FOR BOARD REVIEW — PHASE B NOT AUTHORIZED.

**Phase A.5 decisions and plan (2026-11-20, documentation only):** the Board Operator approved six decisions on the A.4 open points, recorded as D-AUTH-10 to D-AUTH-15 in [auth-migration-phase-a5-board-decisions.md](auth-migration-phase-a5-board-decisions.md) with every implementation authorization Pending, and planned as workstreams WS-1 to WS-7 in [auth-migration-phase-a5-plan.md](../architecture/auth-migration-phase-a5-plan.md). E8, E11 and E12 remain unmet. **No live Paperclip change, credential, user, role, ACL or log change, sandbox, restore or agent/VR test was authorized or performed.** Phase B not authorized. Committed in the Phase A.5 pull request.

**WS-1.1 restore research (2026-11-20, research only):**
- **Sources read:** the installed 2026.1023.0 source; Paperclip `v2026.1117.0` and `master` on GitHub; release notes v2026.1106.0 and v2026.1117.0; docs; upstream issues and pull requests. Labels: source, doc, issue and local read-only.
- **Result:** no supported restore exists. JavaScript-engine backups, the only kind this machine can produce, are not faithful (issue #17854). Recommended isolated candidate: a cold copy of the stopped instance; a `pg_dump` 18 dump only after a tooling decision.
- **Record:** [auth-migration-ws1-restore-research.md](../architecture/auth-migration-ws1-restore-research.md). OQ-025 updated; E8 still not met.
- **Not done:** no restore, backup, upgrade, sandbox or live action. Committed in the WS-1.1 pull request.

## Step 3: Review Package, Phase 2 (2026-11-20)

**Status:** done outside Paperclip; recorded on branch `feat/review-package-phase2-tests`.

**Numbering:** Step 3 follows `review-package.md` §11, as decided in Step 0, so its first subphase is §11 Phase 2 (strict reviewer tests), not the brief's "GitHub API" (§11 Phase 3).

**Result:** all four acceptance conditions met.
- Three planted defects were found at the right `files/head` lines, with a valid verdict block.
- No write, shell or git tool was available to the reviewer.
- Six attempts to read outside the cwd and `current/` were refused.
- No file changed.

**Key finding:** the boundary is Claude Code's `--restricted` flag, which the reviewer profile must carry.

**Not done:** nothing inside Paperclip; G-13 stays open.

**Record:** [review-package-phase2-results.md](../design/review-package-phase2-results.md).

**Next step:** Board review. Then §11 Phase 3, the GitHub source; it needs a throwaway repository and a dedicated read-only token (decision U6, review-package.md §6).

### Step 3, Review Package Phase 3: GitHub source (2026-11-20)

**Status:** code and offline tests done on branch `feat/review-package-phase3-github`; committed in the Phase 3 pull request.

**Done:**
- `review_github.py` implements design §4 option A (PR, compare, paginated file list, trees, blobs, head re-check), and `review_pack.py` gained `--github-pr`/`--github-repo`/`--task-file`.
- The token comes only from Windows Credential Manager and is redacted from all errors.
- 25 new tests against an in-memory fake GitHub. `test_pc.py`: 178 tests OK with `-W error`.

**Not done:** the live run against GitHub. It needs a throwaway repository and a fine-grained read-only token created and stored by the Board (decision U6); see [review-package-phase3-github.md](../design/review-package-phase3-github.md) §3. G-13 stays open.

**Phase 3 live run (2026-11-20):** read-only, on `datpham02/soucean-game` PR #27, with the Board's token from Credential Manager.
- The package built and staged.
- 7/7 blob SHAs matched GitHub and the recomputed bytes.
- The token was found nowhere.
- Not covered live: several pages, a moved head, modified/renamed/deleted files, the 401/403 path.
- Record: [review-package-phase3-github.md](../design/review-package-phase3-github.md) §4.

### Step 3, Review Package Phase 4a: Verdict Relay, offline (2026-11-21)

**Status:** code and offline tests done on branch `feat/review-relay-phase4a`; committed in the Phase 4a pull request.

**Split:** §11 Phase 4 needs a sandbox Paperclip and a real `code-reviewer` run, which need Board approval. 4a builds and tests the relay against a fake Paperclip; 4b is the sandbox validation.

**Done:**
- `review_relay.py` and `pc.py review-relay <KEY> --run-id R`: the five §3.4 checks, the receipt, comment-then-decision order, 3 attempts on network/5xx errors, no retry on 4xx with the Board fallback named, and refusal of a second run for the same head.
- 55 new tests (`test_review_relay.py`). `test_pc.py`: 233 tests OK with `-W error`.
- Record: [review-package-phase4a-relay.md](../design/review-package-phase4a-relay.md).

**Not done:** Phase 4b (V1–V3 in a sandbox). It needs the Board decisions listed in that record, §4. No Paperclip instance or agent was started. G-13 stays open.

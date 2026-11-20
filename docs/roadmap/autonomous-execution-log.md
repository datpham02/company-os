# Autonomous Execution Log

Progress record for the sequential roadmap brief (Steps 0–7). Each step ends with a report to the Board Operator, and the next step starts only on the Board's authorization. Evidence lives in the linked files and commits; this log only summarizes.

## Step 0: current state (2026-11-21)

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

## Step 1: audit of the merged review packager (2026-11-21)

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

# Review Package Phase 5: sandbox end-to-end

- **Date:** 2026-11-21 (server time 02:40–02:48 UTC).
- **Authorization:** the Board Operator in chat: Phase 5 sandbox execution in a dedicated throwaway Paperclip company; "bạn tự bật" (start Paperclip); "xài soucean-game để làm cũng đc" (use `datpham02/soucean-game` as the test repository); "xài soucean-game thì đã có rồi đó" (use the existing GitHub access).
- **Where:** the live Paperclip instance (2026.1023.0, `local_trusted`), new company `RP5 Review Sandbox` (prefix `RPR`, Paperclip's choice). Soucean was not touched (§6).
- **Code under test:** `main` at `6642f18` (merge of PR #48).
- **Status:** the lifecycle ran up to the merge step. The Board Operator decided **not to merge**: PR #28 was closed without merge ("Đóng, không merge"), so the merge step was not exercised. **Phase 5: Partially Accepted.** Acceptance of §12 is partly met (§5). **G-13 stays open.** V3 not tested.
- **Phase definition:** [review-package.md](review-package.md) §11 Phase 5 and §12; earlier records: [phase 4a](review-package-phase4a-relay.md), [phase 4b](review-package-phase4b-live.md).

## 1. Offline baseline (before any live step)

Run in `.claude/skills/paperclip/scripts` at `6642f18`, each with `python -I -W error <file>`:

| File | Result |
|---|---|
| `test_review_pack.py` | 80 tests OK |
| `test_review_github.py` | 25 tests OK |
| `test_review_relay.py` | 68 tests OK |
| `test_pc.py` (includes the three above) | 246 tests OK |

## 2. Preflight and setup

| Item | Evidence |
|---|---|
| Paperclip | Not running at first (connection refused). Started with `runtime/tools/start-studio.cmd` on the Board's word; health `ok`, 2026.1023.0, `local_trusted` |
| Companies before | Soucean (`SOU`, active, 8 agents idle), `GAM` (archived), `REV` (Phase 4b, `code-reviewer` paused). None changed |
| Backup | `POST /api/instance/database-backups`: `paperclip-20261121-094205.sql.gz`, 13,448,259 bytes, `gzip -t` OK. Not proof of a faithful restore (WS-1.1) |
| Packager token | Read from Credential Manager; no expiry warning. Of private repositories it sees only `soucean-game` |
| Roots | A private folder under the Board Operator's home, outside every repository and Paperclip workspace: Review Root, Staging Root, reviewer `cwd`, settings, inputs and outputs |
| Repository | A separate clone of `datpham02/soucean-game` in that private folder, used as the RPR project workspace. The Soucean project's checkout was not used |
| Company | `RP5 Review Sandbox`, `RPR`, budget 0 |
| `code-reviewer` | `claude_local`, `sonnet`, heartbeat off, `env` empty, `--restricted --tools Read,Grep,Glob --strict-mcp-config --permission-mode dontAsk --permission-prompts none --settings <C1> --add-dir <Staging Root>/current`; C1 allows Read, Grep, Glob and denies Edit, Write, NotebookEdit, Bash, PowerShell, WebFetch, WebSearch. Created `paused`; resumed only for each review, paused after |
| `author` | `claude_local`, `sonnet`, heartbeat off, `env` empty (no `GH_TOKEN` binding). The `qa-engineer` allowlist with pushes limited to `RPR-*` branches and npm/docker entries removed |
| Project | `rp5-soucean-game`, isolated `git_worktree` workspaces from `main` |
| Task | `RPR-1`: add `docs/sandbox/rp5-review-check.md` (one file; three acceptance criteria; Write set that file). Review stage: user `local-board`. Released with `pc.py --company RPR release RPR-1` |

## 3. Lifecycle (§11 Phase 5)

| Step | Result | Evidence |
|---|---|---|
| 1 Author Task | **Live.** Paperclip created the worktree and branch `RPR-1-rp5-add-docs-sandbox-rp5-review-check-md-sandbox`; the author committed `8a454e4` (one file) and pushed | Author comments; `git log` |
| 2 PR | **Deviation.** The author's `gh pr create` failed: `gh` had no credential inside the agent run (`git push` worked through Git Credential Manager). The Board-side operator opened [soucean-game#28](https://github.com/datpham02/soucean-game/pull/28) from that branch, titled as a sandbox PR, and commented the URL on RPR-1 | PR #28 |
| 3 Package | **Live.** `review-pack RPR-1 --github-pr 28 …`: `source: github-api`, head `8a454e48`, one file; blob `ea420ee3` = GitHub's file SHA = recomputed from the staged bytes | Manifest |
| 4 Stage | **Live.** Staged with lock; later packages for `e7818ed1` too. Store holds one immutable package per head | Store listing |
| 5 Wake | **Live.** `pc.py --company RPR wake code-reviewer --reason "Review the staged package for RPR-1 at head …"` without `--issue`; runs `1dd2e5e5` and `1de50989` were company-scoped (`issueId` empty) | Run records |
| 6 Review | **Live.** Both runs: init tools `Glob, Grep, Read`; cwd the reviewer folder; every tool call (5 and 6) inside `current/`; no refused call; US$0.033 and US$0.029; each ended with one valid verdict (`approved`, no findings) | Run logs |
| 7–8 Relay | **Live.** Run `1de50989` relayed: findings comment with `relay-receipt: 1de50989… e7818ed1…`, then `approved`; issue `done`, stage `completed`. Audit `relay` | RPR-1 comments |
| 9 Duplicate | **Live.** Same run again: "already relayed", nothing written. Run `1dd2e5e5` for the same head: refused. One receipt comment on the issue | Comments count |
| 10 Stale head | **Live.** After the author pushed `e7818ed`, relaying `1dd2e5e5` (reviewed `8a454e48`) was refused: "the PR head moved to e7818ed11ded" | Audit `refuse` |
| 11 Fallback | **Live.** With the relay refused (T1, check 1), the Board recorded the decision by hand: `pc.py --company RPR request-changes RPR-1 "…"`. The issue returned to the author, who pushed `e7818ed` to the same PR and set `in_review` | RPR-1 history |
| Merge | **Not exercised.** The Board Operator chose to close PR #28 without merge (ADR-009: merge only by the Board) | PR #28 closed, not merged |
| 12 Unstage, cleanup | **Live.** `--unstage` of the unrelayed `8a454e48` review was refused, then `--abandon` (logged); after the relay, `--unstage` succeeded; `--cleanup`: "nothing to clean up" (no issue closed 14+ days); `--status`: empty | Audit log |

**Observed:** the author runs that ended by handing the issue to review (`b3136544`, `cf14d0fe`) are recorded by Paperclip as `cancelled` (`issue_reassigned`, "Cancelled before issue reassignment") although their work (comments, commit `e7818ed`, status change) was done. Only `30cc2025` shows `succeeded`.

## 4. Failure paths

| Case | Result |
|---|---|
| Relay identity not the stage participant | **Live** refused (check 1) |
| Reviewer run from another company (`REV` run `d222eda3`) | **Live** refused: "belongs to another company" |
| Reviewer run created before staging | **Live** refused: "started before the package was staged" |
| Stale PR head | **Live** refused (check 4) |
| Duplicate relay; second run for the same head | **Live** refused |
| Staging held by another issue (`RPR-2` built from PR #28) | **Live** refused: "staging holds RPR-1 … one review at a time"; the `RPR-2` package was built in the store but not staged |
| Package integrity mismatch (one byte appended to staged `patch.diff`) | **Live** refused (check 3: SHA-256); the file was restored from a copy before continuing |
| Unrelayed review cannot be unstaged without `--abandon` | **Live** refused |
| Invalid verdict schema; invalid path, side, severity, line; wrong issue or head in the verdict | **Offline only** (`test_review_relay.py`); a reviewer cannot be made to produce these safely. One wrong-line verdict was refused live in Phase 4b |
| Active reviewer run prevents unstage | **Offline / state-file only.** `--unstage` reads runs from `--state-file` (the Phase 1 stand-in for Paperclip), not from Paperclip, so a live run does not block it. Gap recorded |
| Missing or malformed package data, §5.3 path rules, §5.2 limits | **Offline only** (`test_review_pack.py`); the PR had one small valid file |
| Retention deletion and the 2 GB cap | **Offline only**; live `--cleanup` had nothing eligible |
| 4xx refusal from Paperclip on the decision | **Offline only**; not triggered live |
| V3 (Board-level API access by agents) | **Not tested** (out of scope) |

## 5. §12 acceptance

Legend: **Live** = verified in this sandbox; **Offline** = tests against fakes only; **Source** = code inspection only; **Not tested**; **Failed** = tried and did not behave as specified (none in this run). Offline and source results are not live verification.

| Criterion | Status | Notes |
|---|---|---|
| Packager reads only the GitHub API; no git on agent-writable repositories | **Live** for the API source (manifest `github-api`, blob SHAs match); **Source/Offline** for "no git" | The packager never touched the clone or the worktree |
| §5.3 rules and §5.2 limits refuse | **Offline** | Live input was valid |
| Immutable per head; `READY` last; stale heads refused | **Live**: one package per head, stale head refused. `READY` last: **Offline/Source** | |
| Reviewer has only Read, Grep, Glob; reaches only `current/` besides its cwd; write, shell, git fail | **Live** for tools and the observed reads (2 runs). Write, shell and git attempts: **not attempted live** here (Phase 2, outside Paperclip) | Observation of two runs, not proof of isolation |
| One review staged at a time | **Live** | |
| Relay accepts only §3.4 verdicts; no duplicates; refusal leaves the fallback | **Live** for checks 1–4, duplicates and the fallback; check 5 malformed cases **Offline** (one live in 4b); 4xx path **Offline** | Company-scoped run not bound to one review (§9 of the design) |
| Packager token read-only, selected repositories, never in agent env or log | **Live**: not found in any test file or log; no agent has an `env` binding. Scope: Board-created fine-grained read-only token | |
| Retention, 2 GB cap, cleanup, logged | **Partly**: cleanup and audit **Live**; retention deletion and cap **Offline** | |
| No worktree or branch created, moved or deleted by this work (ADR-006) | **Live** for the packager and relay; Paperclip created the author's worktree and branch normally. The Board side opened a PR from that branch (no branch operation) | |
| G-13 not marked resolved | **Holds** | |

**Phase 5 acceptance ("all §12 criteria in the sandbox"): Partially Accepted.** Not met live: §5.2/§5.3 refusals, `READY` ordering, reviewer write/shell/git attempts, retention deletion and the cap, verdict schema refusals, the 4xx path, and the merge step (closed without merge by the Board's decision).

## 6. Production impact

- Soucean: no run created since Paperclip started (02:40 UTC); its eight agents idle; no issue, agent, setting or workspace changed.
- The packager token appeared in no file of the test folder or the run logs.
- `datpham02/soucean-game` (Board-approved for this test): a branch `RPR-1-…` pushed by the sandbox author; PR #28 closed without merge. `main` unchanged.
- No credential, ACL, membership or agent permission changed. No V3 test.
- Backup: `gzip -t` OK only; no restore was attempted, so the backup is not shown to be restorable.

## 7. Left in place, and cleanup

- Company `RP5 Review Sandbox` (`RPR`): agents `author` and `code-reviewer` **paused**; `RPR-1` `done`. Archive when the Board no longer needs it.
- PR #28: closed without merge. Its branch `RPR-1-…` remains on GitHub (not deleted; delete it when the Board wishes).
- The RPR worktree in the separate clone (Paperclip-owned; not touched).
- The private test folder (packages for `RPR-1` at both heads and for `RPR-2`, audit log, run logs); staging is empty.
- The backup above. Company `REV` (Phase 4b) unchanged.

## 8. Findings (recorded, not implemented)

None of these is fixed by this phase.

1. **The author agent needs a GitHub CLI credential inside its run** to open its own PR. Here it had none (`gh pr create` failed; `git push` worked), so the Board side opened PR #28. Soucean agents get `GH_TOKEN` from a company secret. Providing one is a credential decision for a later, separately approved phase.
2. **`--unstage` takes active runs from the state file**, not from Paperclip. A real reviewer run that is still running may therefore not block `--unstage`.
3. **Paperclip marks a run `cancelled` when it ends by moving the issue to review** (`issue_reassigned`), although the agent finished its work. Tooling and reports must tell this lifecycle state apart from a real failure.
4. **G-13 is unchanged.** A company-scoped reviewer run is not bound to one review or package, and nothing shows that the reviewer read the staged package (design §3.4, §9). A successful Phase 5 lifecycle does not resolve G-13.

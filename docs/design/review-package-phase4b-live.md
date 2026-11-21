# Review Package Phase 4b: live relay test

- **Date:** 2026-11-21 (server time 2026-11-20 17:10–17:15 UTC).
- **Authorization:** the Board Operator in chat: "tôi cho phép test trên thật" (test on the real Paperclip) and "oke tạo đi" (create the `code-reviewer` agent). Review target: `datpham02/soucean-game` PR #27, read-only (Board choice 3).
- **Where:** the live Paperclip instance (2026.1023.0, `local_trusted`), in a **separate throwaway company** `Review Relay Test` (prefix `REV`). No Soucean issue, agent or setting was touched.
- **Phase definition:** [review-package.md](review-package.md) §11 Phase 4; questions V1–V3 in §13; relay code from Phase 4a ([review-package-phase4a-relay.md](review-package-phase4a-relay.md)).
- **G-13 stays open.** This test shows the relay and a strict reviewer working in Paperclip, not isolation in production.

## 1. Setup

| Step | Result |
|---|---|
| Database backup | `POST /api/instance/database-backups`: `paperclip-20261121-001040.sql.gz`, 13,360,857 bytes, `gzip -t` OK. A JavaScript-engine backup: not proof of a faithful restore (WS-1.1) |
| Company | `Review Relay Test` (`REV`), budget 0 |
| Agent | `code-reviewer`, `claude_local`, model `sonnet`, heartbeat off, `maxConcurrentRuns` 1, no `env` (no `GH_TOKEN`, no secrets), `cwd` an empty private folder. `extraArgs`: `--no-session-persistence --restricted --tools Read,Grep,Glob --strict-mcp-config --permission-mode dontAsk --permission-prompts none --settings <C1 strict profile> --add-dir <Staging Root>/current --append-system-prompt <review-only role>`. Paperclip created it `paused` |
| Issue | `REV-1`, created in `backlog`, assigned to `code-reviewer`, execution policy: one review stage with participant user `local-board`. The Board then set `in_review` |
| Package | `review-pack REV-1 --github-pr 27` (Phase 3 code, packager token from Credential Manager): head `7f22f059666b`, staged |

## 2. Answers to V1–V3

**V1, user as stage participant: yes.**
- Setting `in_review` started the review stage with `currentParticipant` = user `local-board`. Paperclip moved the assignee to `local-board` and kept `code-reviewer` as `returnAssignee`.
- The relay, acting as `local-board`, recorded the decision: `PATCH` `in_progress` with a comment was accepted, the stage became `changes_requested`, and the issue went back to the return assignee.

**V2, a run of a non-assignee agent woken for the issue: no.**
- `wake code-reviewer --issue REV-1` was queued and then **cancelled before start** with `issue_assignee_changed` ("Cancelled because issue assignee changed before the queued run could start").
- Source (`server/dist/modules/run-dispatch/domain/policy.js`, `decideIssueOwnership`): an issue-scoped run starts only for the issue's assignee agent, the **agent** participant of the current review stage, an interaction wake, a workspace-busy retry or an authorized recovery. A user-participant stage leaves no slot for an advisory agent.
- **Working arrangement:** wake `code-reviewer` **without an issue** (company scope). That run started and finished normally. The relay now accepts such a run when it is in the issue's company and not scoped to another issue (§4). The staging lock and the verdict's `issue` and `headSha` still bind it to the review.
- The run used the agent's configured `cwd`. Paperclip logged that no project workspace existed and named a fallback workspace folder; Claude Code's init event reported the configured `cwd`. No worktree or branch was created.

**V3, can an agent reach Board endpoints: not tested.**
- The reviewer had only `Read`, `Grep` and `Glob` (init event: `tools: [Glob, Grep, Read]`), so it had no way to make an HTTP call. The Paperclip MCP server Paperclip injects reported `failed` under `--strict-mcp-config`.
- Whether other agents (with `Bash`) can reach Board endpoints in `local_trusted` mode stays open (G-14, OQ-043).

## 3. Runs and relay results

| Run | Wake | Outcome |
|---|---|---|
| `a80451af` | with `--issue REV-1` | Cancelled before start (V2) |
| `460e9932` | no issue | Succeeded, 4 tool calls, all inside `current/`, no refused call, US$0.059. Verdict `changes_requested` |
| `d222eda3` | no issue, with a reminder to cite lines of `files/head/` | Succeeded, 4 tool calls inside `current/`, US$0.050. Verdict `changes_requested`, 3 findings |

**Relay on `460e9932`: refused at check 5.** The reviewer cited `src/pages/index.astro:114`, a line of `patch.diff`; the file has 26 lines. Checks 1–4 had passed. Nothing was written to Paperclip; the audit log has a `refuse` line.

**Relay on `d222eda3`: recorded.**
- Findings comment with `relay-receipt: d222eda3-… 7f22f059…`, then the decision. Issue `in_progress`, stage `changes_requested`; audit `relay` with the run id.
- Findings: `index.astro:14` high (AdSlot never rendered), `ads.css:1` medium (imports a file outside the package), `cover.svg:13` low.
- **Re-run, same run:** "already relayed", nothing written. **Run `460e9932` for the same head:** refused, "already relayed (run d222eda3…)". The issue still has exactly 2 comments.
- `review-pack --unstage` accepted the relayed review.

**Other checks:**
- The packager token was found in none of the test files (UTF-8, UTF-16 and the `github_pat_` prefix).
- The live Soucean company: not touched. Paperclip health OK after the test.

## 4. Code change from this test

`review_relay.py` check 2: when the run is not in `GET /issues/<id>/runs`, the relay reads `GET /heartbeat-runs/<id>` and accepts the run only if its `companyId` equals the issue's and its `issueId` is empty or this issue; agent, status and creation time are checked as before. What this does and does not establish is in the `_company_run` docstring and design §3.4: it does **not** show that the run was started for this review or that it read the staged package. Tests: `Check2CompanyScopedRun` (10, including one that documents that limit); `review-pack` now prints the wake command without `--issue`. `test_pc.py` 243 OK with `-W error`.

## 5. Design consequences (for the Board)

- The reviewer is woken **without an issue**, with a wake reason naming the staged issue and head. Design §1, §3.2–§3.4, §7, §9, §10 and §13 now say so (PR #48 review).
- The reviewer quoted `patch.diff` lines in its first run. `REVIEW.md` should say explicitly that lines are counted in `files/head/<path>` and never in `patch.diff`. The relay already refuses the wrong form.
- After request changes, the issue returns to the stage's return assignee. In this test that was `code-reviewer` (paused, so it was not woken). In production the author is the assignee, so the author is woken, which is the intended behaviour.

## 6. Left in place

- Company `Review Relay Test` with `REV-1` (`in_progress`, assigned to `code-reviewer`) and the agent `code-reviewer`, **paused** so nothing wakes it. Archive the company when the Board no longer needs it.
- The private test folder (`pc-rp4`: package, staging, audit log, run logs) under the Board Operator's home folder.
- The database backup above.

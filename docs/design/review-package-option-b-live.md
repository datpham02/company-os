# Review Package Option B: live sandbox check

- **Date:** 2026-11-21 (server time 03:28–03:42 UTC).
- **Authorization:** the Board Operator in chat asked for a separate sandbox like Phase 5, not Soucean, to check seven cases (§2).
- **Code under test:** branch `feat/review-package-option-b` at `4018ba6` (PR #50, not merged). `test_pc.py` 282 OK before the run.
- **Where:** the live Paperclip instance (2026.1023.0, `local_trusted`), new throwaway company `Option B Review Sandbox` (prefix `OPT`). Database backup first: `paperclip-20261121-102845.sql.gz`, `gzip -t` OK (not proof of a restore).
- **Source:** `datpham02/soucean-game` PR #27, read-only (packager token); parent issues `OPT-1`–`OPT-3`, each with a review stage whose participant is `local-board`; a placeholder `author` agent as their assignee.
- **G-13 stays open.** §3 adds findings that matter for it.

## 1. Setup

| Item | Value |
|---|---|
| `code-reviewer` | `claude_local`, `sonnet`, heartbeat off, no `env`; strict profile as Phase 5 (`--restricted --tools Read,Grep,Glob --strict-mcp-config --permission-mode dontAsk --settings <C1> --add-dir <Staging Root>/current`) |
| `author` | Placeholder, Read only, heartbeat off, no `env`. Meant never to run (see §3, finding 5) |
| Roots | A private folder outside every repository and workspace |
| Timeout simulation | A wrapper around the real API: for the reviewer wake only, it either forwards the request and then raises a timeout (response lost), or raises without sending it (request lost). Every other call is real |

## 2. Results per case

| # | Case | Result | Evidence |
|---|---|---|---|
| 1 | `review-start` creates the sub-issue and wakes the reviewer | **Pass.** `pc.py --company OPT review-start OPT-1` created `OPT-4` (child of `OPT-1`, `backlog`, no project, assigned to `code-reviewer`) and returned run `e75f7168`; lock `reviewStart: started` | Command output; lock |
| 2 | The run is bound to the sub-issue; no unexpected worktree | **Pass.** Run record `scopeKind: issue`, `issueId` = `OPT-4`; workspace `agent_home` fallback, `worktreePath: null`; Claude Code init `cwd` = the configured reviewer folder. The list of `.paperclip/worktrees` folders in the known clones was identical before and after all cases | Run record; worktree snapshots |
| 3 | `contextSnapshot.wakeReason` is what the code checks | **Pass.** `review 183db034-… OPT-1 7f22f059666b`, `triggeredBy: board`, `actorId: local-board`. The verdict echoed `reviewId` and `challenge` correctly; `review-relay` recorded `changes_requested` and closed `OPT-4` | Run record; relay output |
| 4 | Timeout after Paperclip created the run | **Pass.** `OPT-2`: the wake reached Paperclip, the client saw a timeout; lock stayed `waking`. The next `review-start` found run `f4f1a046` by sub-issue, agent, staging time and exact wake reason, recorded it, and woke nothing; a third call reported "already started". The sub-issue had exactly one on-demand run. Relay then succeeded | Outputs; sub-issue runs |
| 5 | Runs list empty right after the wake | **Pass (simulated).** `OPT-3`: the wake was lost before Paperclip; `GET /issues/OPT-6/runs` returned `[]`; the next `review-start` stopped ("may have reached Paperclip … nothing was woken now … do not wake the reviewer by hand"), naming `OPT-6` and its id. **Not observed naturally:** in case 1 the run was already listed (`running`) immediately after the wake returned | Outputs |
| 6 | Parent stays `in_review` | **Pass.** `OPT-1` kept `in_review`, participant `local-board`, and its `updatedAt` through `review-start`, the run and the automatic sub-issue comment; it changed only when `review-relay` recorded the decision (expected). Same for `OPT-2` and `OPT-3` | Issue state before/after |
| 7 | Leftover `staging.op` after a crash | **Pass.** A planted `staging.op` made `review-start` and `review-pack --unstage --abandon` refuse; the staging lock's SHA-256 was unchanged and the file was not taken over. After the Board-style manual removal, `review-start` ran with the preserved `waking` state and stopped safely again. The printed recovery (cancel `OPT-6`, `--unstage --abandon`) then worked | Lock hashes; outputs |

## 3. New findings

1. **An issue-scoped reviewer run gets Paperclip's MCP tools.** The init event listed, besides Read, Grep and Glob, `mcp__Paperclip_projects__create_task`, `create_project`, `set_task_title`, `list_projects`, `list_project_repositories` and two connection tools. In Phases 4b and 5 (company-scoped) the Paperclip MCP server failed to start and none were present. The reviewer called none of them. They would be refused by `--permission-mode dontAsk` with the C1 allow list (Read, Grep, Glob), **not** by `--tools`, which limits built-in tools only. The C1 deny list does not name MCP tools. This weakens the "tools are absent" property of Phase 2 for Option B and needs a fix (for example an explicit MCP deny rule, or no MCP for this agent) and a live refusal test.
2. **Paperclip posts the reviewer's final message as a comment on the sub-issue** (`issueCommentStatus: satisfied`, comment authored by the agent). That message includes the verdict, so the `challenge` becomes visible in Paperclip after the run. It is single-use and bound to the recorded run, so a later stray run cannot reuse it under Option B; but "the challenge never leaves staging" holds only until the run ends.
3. **After the reviewer run, Paperclip queues an `issue_disposition_repair` run** on the sub-issue (still `in_progress`). Both times it was cancelled only because the reviewer had been paused right after its run. Without the pause the reviewer would be woken again. Options: pause the reviewer between reviews (current practice), or close the sub-issue as soon as the run ends rather than at relay time.
4. **The sub-issue moves to `in_progress`** when the run starts (`executionRunId` set), and stays there until the relay closes it.
5. **Agents created through the API reported `paused` but did not stay paused.** The placeholder `author` became `idle` and ran when `review-relay` returned `OPT-1` and `OPT-2` to it (`changes_requested`): two assignment runs and several automation runs (no worktree; about US$0.09 together), plus two `scheduled_retry` runs that ended before they could be cancelled. It was then paused explicitly. Its profile allowed only Read in a private folder. Sandboxes must pause every agent explicitly after creation and check the status.
6. **The run is listed immediately** after the wake (case 1), so the empty-list window of case 5 may be rare in practice; the safe stop remains necessary.

## 4. Not covered

- A natural (not simulated) client timeout.
- A truly concurrent `review-start` against Paperclip (covered offline with threads).
- A crash between creating the sub-issue and recording it (`creating` state) live; covered offline.
- V3; reviewer write, shell, git or MCP attempts (finding 1).

## 5. Production impact and resources left

- Soucean: newest run still from 2026-11-06; all agents idle; nothing changed. `soucean-game`: read only (PR #27).
- Packager token: found in no file of the test folder.
- Left in place: company `OPT` with `author` and `code-reviewer` paused; `OPT-1`/`OPT-2` `in_progress` (returned to the placeholder author), `OPT-3` `in_review`, sub-issues `OPT-4`/`OPT-5` `done`, `OPT-6` `cancelled`; staging empty; the private test folder; the backup.
- Cost: reviewer runs about US$0.10 (case 1) and a similar amount (case 4); placeholder author about US$0.09.

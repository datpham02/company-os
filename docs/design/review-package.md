# Review Package: Diff Handoff for a Read-Only Reviewer

- **Status:** `PROPOSED` (design only; nothing implemented). Part of [OQ-042](../roadmap/open-questions.md#oq-042--reviewer-isolation-g-13). Does not resolve G-13.
- **Date:** 2026-11-20, revised 2026-11-20 with the Board decisions U1, U2, U4, U5, U6 and U7 (§10).
- **Contract owner for:** how the changes of a code Task reach a strict, read-only `code-reviewer`, and how its verdict comes back.

## 0. Problem and constraints

The OQ-042 experiment (2026-11-20) found three things:
- A Claude Code reviewer with only `Read`, `Grep` and `Glob` reviews well when it is handed a diff.
- A reviewer with "read-only" git commands through Bash can write files (`git diff|log|show --output=<file>`), even outside the repository.
- Native Windows gives no OS-level boundary in that setup.

So the reviewer gets **no shell, no git, no write tool and no credentials**. Something else must produce what it reads.

Hard constraints:
- **R1.** The reviewer's tools are `Read`, `Grep` and `Glob` only. No `Bash`, `PowerShell`, git, `Edit`, `Write` or `NotebookEdit`.
- **R2.** No author credentials, Git credentials or packager token in the reviewer's environment.
- **R3.** No write access to the author's Task Workspace, by the reviewer or by anything acting for it.
- **R4.** ADR-006 holds: Paperclip stays the only owner of worktrees. The handoff creates no worktree, checkout or branch.
- **R5.** A separate directory is a convenience, not an isolation boundary. On native Windows, the reviewer, the packager and every agent run as the same user (security-architecture §5).

## 1. Architecture and data flow

**Trust:**
- **[T]** trusted: Board-side code run by the Board Operator.
- **[U]** untrusted: author output, repository content, and the reviewer's output, which is treated as data.

```text
 [U] Author agent ──push──▶ GitHub PR (pinned head SHA)
                                 ▲
                                 │ ③ read-only API (packager token, §6)
 Board Operator                  │
   │ ① pc.py review-pack <KEY>   │
   ▼                             │
 [T] Review Packager ────────────┘
   │ ④ validate, build, manifest (§4, §5)
   ▼
 [T] Review Storage  <Review Root>/store/<KEY>/<head-sha>/   (immutable, READY last)
   │ ⑤ stage (copy, verify) under the staging lock (§7)
   ▼
 [T] Reviewer Staging  <Staging Root>/current/   (one review at a time)
   │ ⑥ Board wakes the reviewer for <KEY> (pc.py wake, manual)
   ▼
 [U] code-reviewer run: claude --print, Read/Grep/Glob only,
     --add-dir <Staging Root>/current  (cwd: the author's worktree; Paperclip decides this)
   │ ⑦ final message ends with a JSON verdict
   ▼
 [T] Verdict Relay (pc.py review-relay <KEY> <run-id>, manual)
   │ ⑧ verify run, issue, reviewer, head SHA, schema (§3)
   ▼
 Paperclip: findings comment + stage decision, or the Board decides by hand (fallback)
   │ ⑨ unstage; ⑩ retention and cleanup (§8)
```

**Every step is started by the Board Operator (U2).** Nothing runs on a Paperclip event, a watchdog or a `provisionCommand`.

**Components:**

| Component | Trust | Reads | Writes | Credentials |
|---|---|---|---|---|
| Review Packager (`pc.py review-pack`) | T | GitHub API (PR, files, blobs) | `<Review Root>/store`, the audit log | Packager token (§6) |
| Stager (part of `review-pack`) | T | the store, Paperclip run status | `<Staging Root>/current`, the staging lock | Board API session |
| `code-reviewer` | U | `<Staging Root>/current`; the author's worktree is also readable (its cwd, §9) | nothing | none |
| Verdict Relay (`pc.py review-relay`) | T | the Paperclip run, its log, the issue, the staged manifest | an issue comment; the decision only as the active stage participant (§3.3); the audit log | Board API session (not exclusive, V3) |

## 2. Approved decisions

| Decision | Approved direction | Status |
|---|---|---|
| U1 | The reviewer returns a JSON verdict. A Board-side Verdict Relay validates it, and records the decision only when its identity is the active review-stage participant (proposed: the Board Operator user; `code-reviewer` advisory, woken by hand). Otherwise it posts findings only and the Board Operator decides manually | Design (§3.3). **Participant arrangement and API compatibility need sandbox validation (V1–V3)** |
| U2 | Manual trigger `pc.py review-pack`. No production `provisionCommand`, no watchdog, no automatic lifecycle | Design (§1, §11) |
| U4 | Limits: 50 files, 1 MB patch, 256 KB per file, 10 context files, 2 GB Review Root, 14 days after closure. Over a limit, fail and request a Task split | Design (§5, §8) |
| U5 | Prefer the GitHub API or an object-only repository. Never trust a working repository | Design (§4): **GitHub API for the first implementation** |
| U6 | A dedicated fine-grained read-only GitHub token for the packager only | Design (§6). No token created |
| U7 | Per-issue storage keyed by head SHA. One `current` staging directory, which is the only one given to the reviewer. Serialized | Design (§7) |

## 3. Verdict return and the Verdict Relay (U1)

### 3.1 Reviewer output

The reviewer writes nothing. Its **final message** must end with exactly one fenced `json` block:

```json
{"schema": "company-os/review-verdict@1",
 "verdict": "changes_requested", "issue": "SOU-12", "headSha": "<40 hex>",
 "findings": [{"path": "src/Calculator.cs", "line": 17, "side": "head", "severity": "critical",
               "title": "Off-by-one in Average", "detail": "…", "fix": "use i < values.Length"}],
 "notReviewed": [{"path": "assets/logo.png", "reason": "binary"}]}
```

Schema rules:
- `verdict` is `approved` or `changes_requested`.
- `severity` is one of `critical`, `high`, `medium` or `low`.
- `side` is `head` or `base`.
- `path` must be one of the files in the manifest.
- `line` must be within that file at that side.
- `changes_requested` needs at least one finding (Paperclip requires a comment for every decision; the relay builds it from the findings).

### 3.2 Paperclip API use

Every endpoint below is already used by `pc.py`. Whether the decision step works for this setup is **unverified**.

| Step | Call | Purpose |
|---|---|---|
| Issue | `GET /api/issues/<KEY>` | `id`, `status`, `executionState` (current stage, participant) |
| Runs | `GET /api/issues/<id>/runs` | the run exists on this issue, with its `agentId`, `status` and `createdAt` |
| Run output | `GET /api/heartbeat-runs/<run-id>/log` | the final message, to extract the verdict |
| Findings | `POST /api/issues/<id>/comments` | the findings as a Board comment, with a relay receipt marker |
| Decision | `PATCH /api/issues/<id>` with `status` and `comment` | approve (`done`) or request changes (`in_progress`), as `pc.py approve` / `request-changes` do today |

### 3.3 Authority: the main open point

The installed Paperclip 2026.1023.0 refuses a stage decision from anyone but the current participant (`issue-execution-policy.js`: "Only the active reviewer or approver can advance the current execution stage"). So a relay acting as the Board **cannot** record a decision for a review stage whose participant is the `code-reviewer` agent. Using the agent's own key would break R2.

The design therefore proposes:
- **Relay identity is the stage participant.** The Task's review stage names the Board Operator user, or a dedicated relay user if Paperclip offers one, as participant. `code-reviewer` is not a stage participant; it is woken for the issue by hand and gives advice.
- The relay records the decision as that user, and only while that user is the active participant (§3.4, check 1).
- Whether an agent woken for an issue it is not assigned to runs normally in the issue's workspace, without a checkout conflict, is **unverified** (V2).
- **Fallback, always available:** the relay posts the findings comment only, and the Board records the decision with `pc.py approve` or `pc.py request-changes`. These already require the issue to wait on the Board.

**Authentication.** Paperclip runs in `local_trusted` mode, where the Board API is reached on loopback without login. The relay therefore has no credential of its own, and any process of the same Windows user can make the same calls. Whether an agent's run can reach Board-level endpoints this way is **unverified** (V3). Under the current setup this is not an exclusive authority. Stronger options would be a Paperclip deployment mode with authenticated Board sessions, or a separate OS account; both are outside this design.

### 3.4 Relay checks (fail closed)

The relay accepts a verdict only when all of these hold:
1. `<KEY>` resolves to an issue in `in_review`, and its current participant is the relay's identity.
2. `<run-id>` is in `GET /issues/<id>/runs`, its `agentId` is `code-reviewer`, its status is finished successfully, and it was created after the current staging time.
3. The staging lock names this `<KEY>` and `headSha`, and the staged manifest still verifies against the store.
4. The PR head on GitHub still equals `headSha`. If the author pushed since, the review is stale.
5. Exactly one verdict block, valid against the schema; `issue` and `headSha` equal the staging lock; every finding points into the manifest.

Any failed check stops the relay with a reason, and nothing is recorded.

### 3.5 Duplicates, retries and refusals

- **Receipt.** Every comment the relay posts carries `relay-receipt: <run-id> <headSha>`. Before posting, the relay looks for that receipt on the issue and in the audit log. If it is found, it does nothing ("already relayed"), so re-running the command is safe.
- **Order.** Post the comment first, then the decision. If the decision fails after the comment, re-running finds the receipt, skips the comment and retries only the decision.
- **Transient errors** (network, HTTP 5xx): up to 3 attempts with backoff, then stop and report. No queue, no background retry.
- **Refusal** (HTTP 4xx, for example 422 "Only the active reviewer…"): no retry. The relay leaves the findings comment, writes the refusal to the audit log, and tells the Board to decide by hand (fallback).
- **A second verdict for the same head** (a new run): refused while a receipt exists for that head. The Board decides which review stands.

## 4. Source of changes (U5)

**Risk of a working repository as input.** The author agent can write that repository's `.git/config`, `.gitattributes`, hooks and files. Git commands that read the index or worktree can run author-controlled programs as the Board user: fsmonitor, hooks, filters, textconv and external diff. Even tree-to-tree plumbing reads the repository-local config. **The packager never reads the author's worktree or its repository.**

| | **Option A: GitHub API** (recommended first) | Option B: object-only repository |
|---|---|---|
| Source | PR metadata and blobs over HTTPS | A packager-owned bare repository, fetched from GitHub |
| Runs git locally | No | Yes (`fetch` and plumbing), in a repository whose config only the packager writes |
| Repository-controlled code | None | None if: a bare repository, no checkout, `core.hooksPath` set to null, `GIT_CONFIG_NOSYSTEM=1`, global config nulled, no `.gitattributes` applied (no worktree), and only `cat-file`, `ls-tree`, `diff-tree --no-ext-diff --no-textconv` and `merge-base` |
| Integrity | Each blob's git SHA-1 is recomputed from its content and compared with the tree entry and the PR file list | git verifies objects on fetch (`fetch.fsckObjects=true`); the commit and tree chain from the pinned SHA |
| Limits | Rate limits; the PR files list paginates (100 per page); a file's `patch` is omitted when too large | Disk; first fetch time |
| Shared with Paperclip | Nothing | Nothing (a separate bare repository, not the Primary Checkout) |

**Recommendation: Option A** for the first implementation:
- it has no local git process and no repository on the Board side;
- it reads exactly what the Board would merge;
- the 50-file and 1 MB limits keep it within rate limits.

Option B is the fallback if API limits or completeness become a problem. It needs its own review before use.

**Option A procedure** (all reads, using the packager token):
1. `GET /repos/{o}/{r}/pulls/{n}`: take `head.sha` and `base.sha`; refuse if the PR is closed or its head repository is a fork the token cannot read.
2. `GET /repos/{o}/{r}/compare/{base}...{head}`: take `merge_base_commit.sha`. Use the merge base, not the base tip, for "before" content.
3. `GET /repos/{o}/{r}/pulls/{n}/files?per_page=100&page=…`: read every page until it is empty. The number of files must equal `changed_files` from step 1, otherwise refuse.
4. For each file, get the before and after blobs by SHA (`GET /repos/{o}/{r}/git/blobs/{sha}`, base64). Recompute `sha1("blob " + len + "\0" + bytes)` and compare it with the blob SHA. The head blob SHA comes from the tree at `head.sha` (`GET /git/trees/{head}?recursive=1`, or per path).
5. Build `patch.diff` from the two blob sets with a fixed in-process diff (unified, 5 lines of context). Never use the `patch` field as the only source, since GitHub omits it for large files.
6. Re-read step 1. If `head.sha` changed, discard and stop ("PR head moved; run again").
7. Context files (the Task's Read set): blobs at `head.sha`, verified the same way.

## 5. Package format, limits and validation (U4)

### 5.1 Layout

```text
<Review Root>/                        # outside every repository and the Workspace Root; never committed or synced
  store/<ISSUE-KEY>/<head-sha>/       # immutable once READY
    READY                             # written last; a package without READY does not exist
    manifest.json
    REVIEW.md                         # brief: Task goal, acceptance criteria, write set, reviewer instructions, verdict schema
    patch.diff
    files/head/<repo path>            # after-state of A/M/R/C files
    files/base/<repo path>            # before-state (merge base) of M/D/R/C files
    context/<repo path>               # Read-set files at head
  audit.log                           # append-only JSON lines (§8)
<Staging Root>/                       # a separate folder, NOT inside <Review Root>
  current/                            # a verified copy of exactly one package
  staging.lock
```

- Paths keep the repository layout, so the finding `src/Calculator.cs:17` refers to `files/head/src/Calculator.cs` line 17.
- `manifest.json` uses the fields of schema `company-os/review-package@1`:
  - `issue`, `repository`, `pullRequest`, `baseSha`, `headSha`, `mergeBaseSha`, `source` (`github-api`), `limits`;
  - per file: `path`, `status`, `oldPath`, `mode`, `binary`, `encoding`, `bytes`, `gitBlobSha` (before and after), `sha256`, `included`;
  - `notReviewable`, `patchSha256`, `createdAt`, `packagerVersion`.

### 5.2 Limits (approved defaults)

| Limit | Value | Over the limit |
|---|---:|---|
| Changed files | 50 | **Refuse**: "too large to review; split the Task" |
| `patch.diff` size | 1 MB | **Refuse**: split the Task |
| Any changed text file (before or after) | 256 KB | **Refuse**: split the Task, or the Board reviews that file by hand |
| Context files (Read set) | 10 | **Refuse**: narrow the Read set |
| `<Review Root>` total | 2 GB | Clean up eligible packages (§8); if still over, **refuse** new packages |

- **Nothing is dropped silently.**
- Content that cannot be reviewed as text (binary files, symlinks, submodules) is never truncated. It is listed in `manifest.json` `notReviewable` and at the top of `REVIEW.md`, and the reviewer must repeat it in `notReviewable`.
- A Read-set file missing at head refuses the package.

### 5.3 Validation (fail closed)

| Check | Rule | On failure |
|---|---|---|
| Inputs to `review-pack` | `<KEY>` matches `^[A-Z]+-\d+$`; the issue exists, is `in_review` and has a code project; its PR is found from the Task's branch or the PR link in the issue; the repository is in the token's allowed list | Refuse; nothing written |
| Paths | Reject: absolute paths, drive letters, `..`, empty segments, NUL or control characters, `:` (alternate data streams), trailing dot or space, Windows reserved names (`CON`, `NUL`, `COM1`…), a component over 255, the total path length limit, case-insensitive collisions. After joining, the resolved real path must stay inside the package folder | **Refuse** the package |
| Windows short names | A component shaped like an 8.3 name (`LONGFI~1.CS`, `PROGRA~1`) can alias another file when 8.3 names are enabled (added after the Phase 1 audit, 2026-11-20) | **Refuse** the package |
| Links under the roots | The packager never follows a symlink or junction below `<Review Root>` or `<Staging Root>`, and a package never contains one. Any process of the same user can plant one (Phase 1 audit) | **Refuse**; `--cleanup` logs and skips a linked trash entry |
| Symlinks (`120000`), submodules (`160000`) | Never created on disk; target or commit recorded as text | `notReviewable` |
| Binary | A NUL byte in the first 8 KB, or GitHub reports no text diff | `notReviewable` (sizes and blob SHAs listed) |
| Encoding | Not valid UTF-8 | Included raw, `encoding: unknown`, listed in `REVIEW.md` |
| Integrity | Every blob SHA recomputed (§4). Every file's SHA-256 in the manifest. `patchSha256` | Refuse |
| Staleness | PR head changed during the build | Discard the build and refuse |
| Atomicity | Build in `store/<KEY>/.tmp-<random>/`, rename to `<head-sha>/`, write `READY` last. An existing `<head-sha>/` with `READY` is reused, never overwritten | Leftover `.tmp-*` is removed by the next run of the same key |

Package content is untrusted input for the reviewer, and code comments may carry prompt injection. `REVIEW.md` puts its fixed instructions first, and quotes everything taken from the Task, the PR or the repository afterwards, inside one fence longer than any backtick run in that text (Phase 1 audit). It tells the reviewer to treat all of it as data. With no write tools, the worst case is a manipulated verdict. The Board's approval and merge (ADR-009) stay the last gate.

## 6. Packager GitHub token (U6)

- **Type:** a **fine-grained personal access token** dedicated to the packager. Never an agent's `GH_TOKEN`, and never a broad classic token when a dedicated token can be used.
- **Repository access:** "Only select repositories", listing each game and web repository the studio reviews. Adding a repository is a Board action.
- **Permissions (read-only):**
  - Metadata: read (always required);
  - Contents: read (blobs, trees, compare);
  - Pull requests: read (PR and file list).
  - No other permission. Contents and Pull requests have **no write**.
- **Storage:** Windows Credential Manager, under a generic credential such as `company-os/review-packager`. Not in Git, not in `config/`, not in Paperclip secrets, and not bound to any agent. The packager reads it at start, passes it only in the `Authorization` header, and never logs it. Error messages are redacted.
- **Expiry:** at most 90 days, recorded in the operations runbook. The packager warns when fewer than 14 days remain (from the token metadata, if the API exposes it; otherwise from the recorded date).
- **Rotation:** create the new token, store it, run one dry `review-pack`, then revoke the old token in GitHub.
- **Revocation:** revoke at once if it may have leaked. The packager treats HTTP 401 or 403 as "token invalid or revoked" and refuses, with no fallback to another credential.
- **Not visible to agents:** it is never in an agent's environment. On the same Windows user, a determined agent process could still read Credential Manager entries (§9).

## 7. Cross-task isolation: storage and staging (U7)

- **Storage** (`<Review Root>/store/<KEY>/<head-sha>/`): one immutable package per issue and head. Only the packager creates or deletes it. It is never given to the reviewer.
- **Staging** (`<Staging Root>/current/`): a verified copy of exactly one package. It is the only path passed to the reviewer (`--add-dir <Staging Root>/current`, a fixed `extraArgs` value of the `code-reviewer` agent). It sits outside `<Review Root>`, so the reviewer cannot reach the store through it. Copies, not links or junctions.
- **Staging lock** (`staging.lock`, JSON): `{issue, headSha, packagePath, stagedAt, stagedBy, runId|null}`.

Staging is one-at-a-time:
1. `review-pack <KEY>` builds or reuses the package, then stages it.
2. Staging requires that no lock exists, or that the lock names the same issue and head (re-staging is a no-op).
3. To replace another issue's staging, the Board runs `pc.py review-pack --unstage`. That command refuses while the locked review's run is active (`queued`, `starting`, `running`). It also refuses while that review is not yet relayed, unless `--abandon` is given, which is logged.
4. Staging verifies the copy against the store's manifest (every SHA-256), then writes `current/READY`.
5. **Serialization:** only one `code-reviewer` review is in flight. The Board wakes `code-reviewer` only for the issue named in the lock; `review-pack` prints the exact `pc.py wake` command. A second review waits.
6. **Crash or abandoned staging:**
   - A lock whose run is finished, failed or cancelled, or that has had no run for 24 hours, is reported by `review-pack --status` as stale.
   - The Board clears it with `--unstage --abandon`.
   - Nothing is cleared automatically.
   - `current/` is cleared only by `--unstage` and after a successful relay.

**This is not an OS-level boundary.** All agents run as the same Windows user:
- any agent process with a shell (authors on Cursor have one) can read the store, the staging folder and the lock, and can change them;
- staging only keeps the strict reviewer's own tools away from other issues' packages.

## 8. Retention, cleanup and audit (U4)

- **Retention starts when the issue reaches `done` or `cancelled`**, and runs for 14 days. Packages of open issues are never deleted.
- **Open detail (V5):** Paperclip's `done` is not proof of merge (ADR-009 needs a separate GitHub merge). Should retention wait for a confirmed merge or closed PR as well?
- **Cleanup** runs only when the Board runs `pc.py review-pack --cleanup`. It removes packages of closed issues older than 14 days, oldest first. No scheduled task.
- **When the 2 GB cap is reached:** new builds first trigger a cleanup of eligible packages. If the store is still over the cap, the build is **refused** with the size and the list of the largest open-issue packages. The Board decides; nothing open is deleted.
- **Deletion is two-step:** rename to `store/.trash/<KEY>-<head>-<time>/`, then delete. A failure is logged and retried at the next `--cleanup`. A package half-deleted never keeps its `READY`, because `READY` is removed first. The staged package is never deleted.
- **Audit log** (`<Review Root>/audit.log`, append-only JSON lines) records `build`, `reuse`, `refuse`, `stage`, `unstage`, `abandon`, `relay`, `relay-refused`, `cleanup` and `cleanup-failed`. Each entry has a timestamp, the issue, the head SHA, the run id and the reason. It never holds tokens or source content. The log is kept for one year (rotation by size, never deleted on cleanup).

## 9. Security boundaries and remaining risks

**What the design gives:**
- the reviewer's toolset has no write, shell or git path (verified outside Paperclip in the OQ-042 experiment);
- no git runs on any repository an agent can write;
- the packager token never reaches an agent's environment;
- the reviewer's tools see only one package.

**What it does not give:**
- **No OS boundary.** Native Windows gives no filesystem isolation in the tested setup. Packager, relay, reviewer and every agent run as the same user. Claude Code's tool permissions are not OS isolation.
- **Paperclip still starts review runs in the author's worktree.** The reviewer can read it, and anything else its tools can reach.
- **Tampering.** A same-user agent process can change staging or stored packages. Checksums in the manifest detect accidental corruption only, because a writer who can change the data can also change the manifest. The relay re-checks the head SHA against GitHub, which limits but does not prevent a manipulated review.
- **Board authority in `local_trusted` mode** is not exclusive to the relay (§3.3, V3).
- **G-13 is not resolved** by this design. Other review paths are unchanged until a strict `code-reviewer` handles every code review.
- **Cursor must never be used as `code-reviewer`** (OQ-033: no allowlist or permission key).

**Stronger isolation would need one of:**
- separate Windows accounts: agents under one account, the packager and relay under another, with NTFS ACLs that give agents no access to `<Review Root>` and the reviewer read-only access to `<Staging Root>` (OQ-027);
- containers or VMs per agent; the studio runs agents natively today (ADR-013);
- a future Paperclip feature: a read-only per-stage workspace holding the PR head.

## 10. Paperclip integration (no ADR-006 change)

| Need | Native Paperclip | Company OS (custom, not built) |
|---|---|---|
| Review stage | `executionPolicy` review stage. Under U1 the participant is the relay's user identity (§3.3) | Stage set by `pc.py create --review <user>`, needs a small change (V1) |
| Reviewer agent | `claude_local`, engine `cli`, `extraArgs`: `--restricted --tools Read,Grep,Glob --strict-mcp-config --permission-mode dontAsk --permission-prompts none --settings <reviewer settings> --add-dir <Staging Root>/current` | Agent definition, settings file; no secrets bound |
| Trigger | Manual wake: `POST /agents/<id>/wakeup` with the issue (`pc.py wake`) | `pc.py review-pack` (build, stage, print the wake command) |
| Verdict | Run log and issue APIs (§3.2) | `pc.py review-relay` |
| Worktrees | Created and cleaned by Paperclip only | Never touched; the packager owns only `<Review Root>` and `<Staging Root>` |

**A future automatic trigger (not designed for build now).** A later phase could call the same `review-pack` and `review-relay` code from the review-wake watchdog or from a project `provisionCommand`. Either needs:
- answers on run ordering and failure behaviour (OQ-042 V4);
- its own approval, because both act on production issues;
- the same staging serialization;
- an unchanged manual path as the fallback.

## 11. Implementation phases

Progress (2026-11-20): Phase 1 merged (PR #29, audited in PR #30). Phase 2 run outside Paperclip, all acceptance conditions met ([review-package-phase2-results.md](review-package-phase2-results.md)). Phase 3 done, with a first read-only live run on `datpham02/soucean-game` PR #27 ([review-package-phase3-github.md](review-package-phase3-github.md)). Phase 4 split (2026-11-21): 4a, the `review-relay` command with offline tests against a fake Paperclip, is done ([review-package-phase4a-relay.md](review-package-phase4a-relay.md)); 4b was run on the live instance in a throwaway company (2026-11-21, [review-package-phase4b-live.md](review-package-phase4b-live.md)): V1 yes, V2 no (the reviewer must be woken without an issue), V3 not tested; the relay recorded a decision and refused a bad verdict and a duplicate. Phases 5–6 not started. G-13 stays open.

| Phase | Deliverables | Acceptance | Depends on | Stop if |
|---|---|---|---|---|
| 0 Design approval | This document, reviewed | Board approves the design and the open points it accepts | — | The Board rejects the approach |
| 1 Packager CLI | `pc.py review-pack` built from fixture data (recorded GitHub API responses), store, staging, lock, cleanup, audit log; unit tests | Every §5.3 rule and §5.2 limit has a test; atomic build; staging refuses a second issue; no files outside the two roots change | Phase 0 | A rule cannot be enforced without running git on an agent-writable repository |
| 2 Strict reviewer tests | Repeat the OQ-042 experiment on a staged package | Defects found with correct `files/head` lines; verdict block valid; write, shell and git attempts all fail; the store and other packages are not reachable through the reviewer's tools | Phase 1 | The reviewer can read outside `current/` and the cwd, or write anything |
| 3 GitHub source | Option A against a throwaway GitHub repository with the dedicated token | Blob SHAs verified; pagination complete; head-moved and missing-patch cases refused; token never logged | Phase 1; a token created by the Board | The token needs more than read permissions |
| 4 Paperclip sandbox and relay API | A separate sandbox company: review stage with a user participant, a manual wake of `code-reviewer`, `review-relay` | V1–V3 answered; the decision is recorded or refused as §3.5 says; the fallback works | Phases 1–3; Board approval to start Paperclip | The sandbox would touch the production company, or Paperclip refuses every relay identity |
| 5 Sandbox end-to-end | Author Task, PR, package, review, relay, decision, merge, cleanup | All §12 criteria in the sandbox | Phase 4 | Any criterion fails |
| 6 Production proposal | Written proposal: agent, profile, stages, runbook, token. **Separate approval** | — | Phase 5 | — |

## 12. Acceptance criteria (for the finished work, not met by this document)

- [ ] The packager reads only the GitHub API (or an object-only repository after its own review). No git runs on a Task Workspace, the Primary Checkout or any repository an agent can write.
- [ ] Every §5.3 rule refuses as specified. Every §5.2 limit refuses with "split the Task". Nothing is dropped silently.
- [ ] Packages are immutable per head SHA, `READY` is written last, and stale heads are refused.
- [ ] The reviewer's tools are `Read`, `Grep` and `Glob`. It reaches only `<Staging Root>/current` besides its cwd. Write, shell and git attempts fail.
- [ ] Only one review is staged at a time. Another issue's active staging cannot be replaced.
- [ ] The relay accepts only a verdict that passes §3.4. A re-run never duplicates a comment or decision. A refusal leaves the human fallback.
- [ ] The packager token is read-only, limited to selected repositories, and never in an agent environment or a log.
- [ ] Retention, the 2 GB cap and cleanup behave as §8 says, and are logged.
- [ ] No worktree or branch is created, moved or deleted (ADR-006).
- [ ] G-13 is not marked resolved by this work alone.

## 13. Open validation questions

- **V1 Stage participant.** Can a review stage name the Board Operator user, or a dedicated relay user, while `code-reviewer` is woken for the issue without being a participant? Does `pc.py create --review` need a user option?
- **Answered 2026-11-21** ([review-package-phase4b-live.md](review-package-phase4b-live.md)): V1 yes; V2 no, Paperclip cancels an issue-scoped run of a non-assignee, non-participant agent, so the reviewer is woken without an issue; V3 not tested (the strict reviewer has no network tool).
- **V2 Non-assignee run.** Does a `code-reviewer` woken for an issue it is not assigned to run without a checkout conflict, and in which cwd?
- **V3 Board authority.** In `local_trusted` mode, can an agent's own process reach Board-level endpoints? If yes, the relay's authority is not exclusive, and that must be recorded as a risk or fixed by the deployment mode.
- **V4 Automatic trigger.** Ordering and failure behaviour of the watchdog or `provisionCommand` path (future phase only).
- **V5 Retention start.** Issue closure (approved default) or confirmed merge?
- **V6 Fork PRs.** Are PRs from forks in scope? The token may not read them.

## Related documents
[../roadmap/open-questions.md](../roadmap/open-questions.md) (OQ-027, OQ-033, OQ-035, OQ-042) · [../architecture/stage1-gap-analysis.md](../architecture/stage1-gap-analysis.md) (G-13) · [../architecture/security-architecture.md](../architecture/security-architecture.md) · [../decisions/ADR-006-git-worktree-for-concurrent-tasks.md](../decisions/ADR-006-git-worktree-for-concurrent-tasks.md) · [../decisions/ADR-009-approval-before-merge.md](../decisions/ADR-009-approval-before-merge.md) · [../../knowledge/company/standards/task-contract.md](../../knowledge/company/standards/task-contract.md)

# Review Package: Diff Handoff for a Read-Only Reviewer

- **Status:** `PROPOSED` (design only; nothing implemented). Part of [OQ-042](../roadmap/open-questions.md#oq-042--reviewer-isolation-g-13). Does not resolve G-13.
- **Date:** 2026-11-20
- **Contract owner for:** how the changes of a code Task reach a strict, read-only `code-reviewer`, and how its verdict comes back.

## 0. Problem and constraints

The OQ-042 experiment (2026-11-20) found:
- A Claude Code reviewer with only `Read`, `Grep` and `Glob` reviews well when it is handed a diff.
- A reviewer with "read-only" git commands through Bash can write files (`git diff|log|show --output=<file>`), even outside the repository.
- Native Windows gives no OS-level boundary in that setup.

So the reviewer gets **no shell, no git, no write tool and no credentials**. Something else must produce what it reads.

Hard constraints:
- **R1.** Reviewer tools: `Read`, `Grep`, `Glob` only. No `Bash`, `PowerShell`, git, `Edit`, `Write` or `NotebookEdit`.
- **R2.** No author or Git credentials in the reviewer's environment.
- **R3.** No write access to the author's Task Workspace, by the reviewer or by anything acting for it.
- **R4.** ADR-006: Paperclip stays the only owner of worktrees. The handoff creates no worktree, checkout or branch.
- **R5.** A separate directory is a convenience, not an isolation boundary. On native Windows, the reviewer and the packager run as the same user (security-architecture §5).

## 1. Architecture and data flow

```text
 Author agent ──push──▶ GitHub PR (head SHA)                  Paperclip
      │                                                          │ issue → in_review,
      ▼                                                          │ stage participant = code-reviewer
 Task Workspace (worktree, Paperclip-owned)                      │
      │  (packager never reads or writes it)                     ▼
      ▼                                             ┌──────────────────────────┐
 Shared git object store ◀── read-only plumbing ──  │ Review Packager (trusted, │
                                                    │ Company OS, Board side)  │
 GitHub API ◀── PR head/base SHA, read-only ─────── │ builds + validates       │
                                                    └────────────┬─────────────┘
                                                                 │ writes (atomic)
                                                                 ▼
                                   <Review Root>/<ISSUE-KEY>/<head-sha>/   (package, then READY)
                                                                 │ Read / Grep / Glob only
                                                                 ▼
                                           code-reviewer run (claude --print, strict profile)
                                                                 │ final message = verdict JSON
                                                                 ▼
                                      Verdict Relay (trusted) ──▶ Paperclip decision + comment
```

**Steps:**
1. The author pushes the Task Branch and opens a PR (development-cycle).
2. The issue enters the `review` stage with `code-reviewer` as participant.
3. The **Review Packager** resolves the PR for the issue and reads its head and base SHAs from GitHub.
4. It checks that both commits exist in the local object store, then builds the package from those two commits only.
5. The package is built in a temporary folder and renamed into place. A `READY` file is written last.
6. The reviewer runs (a Paperclip wake, see §6). Its prompt names the package path. It reads the package and writes nothing.
7. The reviewer ends with a verdict block in a fixed format.
8. The **Verdict Relay** reads the run output and records the decision and findings on the issue (§3.4, open question U1).

**Two trusted components, both outside the reviewer:**

| Component | Runs as | Reads | Writes |
|---|---|---|---|
| Review Packager | Board side (`pc.py` command, later the watchdog) | git objects through plumbing, GitHub PR metadata | only `<Review Root>` |
| Verdict Relay | Board side | the reviewer's run log via the Paperclip API | the Paperclip issue (decision, comment) |

## 2. Recommended approach and alternatives

**Recommended: a read-only review package** (option C below). It holds the patch, full before and after text of each changed file, the Task's review brief, and a manifest. It is built from the PR's **pinned head and base SHAs** with tree-to-tree git plumbing, and checked against GitHub.

| Option | What the reviewer gets | Pros | Cons |
|---|---|---|---|
| A. Patch file only | `patch.diff` | Smallest; simplest | Line numbers lack context; the reviewer would read the author's worktree for the rest, and that worktree may hold uncommitted or unpushed changes |
| B. Snapshot of changed files plus metadata | After-state of changed files, manifest | Exact line references | No hunks; harder to see what changed; no base for deleted or modified lines |
| **C. Review package (patch plus before/after files plus brief plus manifest)** | All of A and B, the acceptance criteria and the write set | Exact commit; self-contained; works without the worktree; checksummed | More code (validation, limits, retention); disk use |
| D. Diff from the GitHub API only | Patch and file contents fetched by the packager over HTTPS | No local git at all, so untrusted repo config cannot run code | Needs network and a token; rate limits; large PRs paginate |

Choose C, built from local git objects, with the SHAs pinned and checked against GitHub. Keep D as the fallback when objects are missing or the repository config cannot be trusted (§5).

## 3. Package format

### 3.1 Layout

```text
<Review Root>/                      # outside every repository and Workspace Root; not synced to cloud
  <ISSUE-KEY>/<head-sha>/           # e.g. SOU-12/3f2a…; one package per reviewed head
    READY                           # empty; written last. No READY means not ready, so do not review
    manifest.json
    REVIEW.md                       # review brief: task goal, acceptance criteria, write set, instructions
    patch.diff                      # unified diff base..head, 5 lines of context
    files/head/<repo path>          # full text at head for added, modified and renamed files
    files/base/<repo path>          # full text at base for modified, deleted and renamed files
    context/<repo path>             # optional: unchanged files named in the Task's Read set (bounded)
```

- Repository paths are kept as they are, so a finding `src/Calculator.cs:17` refers to `files/head/src/Calculator.cs` line 17. That is the same file at the PR head.
- Files are written as raw blobs (`git cat-file blob <sha>`), with no smudge filter, line-ending change or textconv.

### 3.2 `manifest.json`

```json
{
  "schema": "company-os/review-package@1",
  "packager": { "version": "0.1.0" },
  "createdAt": "2026-11-20T10:00:00Z",
  "issue": { "key": "SOU-12", "id": "<uuid>", "project": "<project id>" },
  "repository": "owner/name",
  "pullRequest": { "number": 41, "url": "https://github.com/owner/name/pull/41" },
  "baseSha": "<40 hex>", "headSha": "<40 hex>", "mergeBaseSha": "<40 hex>",
  "verifiedAgainstGitHub": true,
  "limits": { "maxFiles": 50, "maxPatchBytes": 1048576, "maxFileBytes": 262144, "maxContextFiles": 10 },
  "files": [
    { "path": "src/Calculator.cs", "status": "M", "oldPath": null, "mode": "100644",
      "binary": false, "encoding": "utf-8", "bytes": 812,
      "headSha256": "<hex>", "baseSha256": "<hex>", "included": "full" }
  ],
  "omitted": [ { "path": "assets/logo.png", "reason": "binary" } ],
  "warnings": [],
  "patchSha256": "<hex>"
}
```

- `status` is one of `A`, `M`, `D`, `R` or `C` (with `oldPath`), or `T` for a type change.
- `included` is one of `full`, `patch-only`, `metadata-only` or `omitted`.

### 3.3 Reviewer access
- **Diff:** `patch.diff`.
- **Source:** `files/head` and `files/base`, plus `context/` for the Read set.
- **Line references:** paths and line numbers of `files/head`; for removed lines, `files/base` labelled `(base)`.
- **Instructions:** `REVIEW.md` (generated from the issue's goal, acceptance criteria, write set and the reviewer checklist).
- **Package location:** the run is given one fixed extra directory, `--add-dir <Review Root>`. The prompt, built from the issue key, names `<Review Root>/<ISSUE-KEY>/<head-sha>/`.

The reviewer is told to read only the package. A deny rule on the author's worktree (`Read(./**)`) would make that technical. It is untested (U3).

### 3.4 Verdict return

The reviewer writes nothing. Its **final message** must end with one fenced block:

```json
{"verdict": "changes_requested", "issue": "SOU-12", "headSha": "<40 hex>",
 "findings": [{"path": "src/Calculator.cs", "line": 17, "side": "head", "severity": "critical",
               "title": "Off-by-one in Average", "detail": "…", "fix": "use i < values.Length"}]}
```

The **Verdict Relay** reads the run log through the Paperclip API (`GET /heartbeat-runs/{id}/log`, as `pc.py log` already does). It accepts the block only when all of these hold:
- the JSON parses against the schema;
- `issue` and `headSha` match the package;
- the package's head is still the PR head.

It then posts the findings as a comment and records the stage decision.

**How the decision is recorded is open (U1).** Paperclip expects the decision from the stage participant. Recording it on the reviewer's behalf may need the reviewer's identity, which would break R2, or a Board-side path whose semantics are unverified. The alternative is to let the reviewer call one Paperclip reporting helper. That puts a shell back, which is exactly what failed in the experiment, so it is the fallback only after its own experiment.

## 4. Validation (packager; fail closed)

The packager treats the repository, its config and its contents as **untrusted** (an author agent can write `.git/config`, `.gitattributes` and file contents).

| Check | Rule | On failure |
|---|---|---|
| PR and SHAs | The PR is found from the issue's branch or link. Head and base SHAs come from GitHub. Both objects exist locally (`git cat-file -e`). The local branch tip equals the PR head | Refuse: "head not pushed / objects missing"; fallback D or Board |
| Git commands | Tree-to-tree plumbing only: `rev-parse`, `cat-file`, `ls-tree`, `diff-tree -p -M --no-ext-diff --no-textconv`. Never commands that read the index or worktree (`status`, `diff` without two trees), so `core.fsmonitor` and hooks never run. Run with `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL` set to the null device, and `-c core.hooksPath=<null>`. Repository-local config stays untrusted (U5) | Refuse on any non-zero exit |
| Paths | Reject or encode: absolute paths, drive letters, `..`, empty segments, NUL or control characters, `:` (alternate data streams), trailing dot or space, Windows reserved names (`CON`, `NUL`, `COM1`…), components over 255, total over the path limit. Reject case-insensitive collisions on Windows. After joining, the resolved real path must stay inside the package folder | Skip the file: `omitted` with a reason. Refuse the package if a changed path is rejected |
| Symlinks, submodules | Mode `120000` is metadata only (target recorded as text, never created). Mode `160000` is metadata only | `metadata-only` |
| Binary | numstat `-`, a NUL byte in the first 8 KB, or a file larger than `maxFileBytes` | `metadata-only` (sizes and hashes) |
| Encoding | Not valid UTF-8 | Contents included raw; `encoding` set to `unknown`; warning |
| Size | Over `maxFiles` changed files or `maxPatchBytes` | **Refuse:** "too large to review; split the Task" (task-contract §2 size). Context files over the limit are dropped with a warning |
| Missing context | A Read-set file is missing at head | Warning in the manifest; review continues |
| Integrity | Before `READY`: compute and record `sha256` of every file; recompute the patch from the stored blobs | Refuse |
| Staleness | The PR head moved during the build | Discard and rebuild |

Content is untrusted input for the reviewer too: code comments may carry prompt injection. `REVIEW.md` tells the reviewer to treat package content as data. With no write tools, the worst case is a manipulated verdict. The Board's approval and merge (ADR-009) remain the last gate.

## 5. Security boundaries and remaining risks

**What the design gives:**
- the reviewer's toolset has no write, shell or git path (verified outside Paperclip in the OQ-042 experiment);
- the reviewer needs nothing from the author's worktree;
- git runs only in a trusted Board-side component, restricted to tree-to-tree plumbing.

**What it does not give:**
- **No OS boundary.** The packager, the reviewer and every agent run as the same Windows user. The reviewer's limits are Claude Code permission checks, not filesystem isolation (OQ-027).
- **G-13 is not fixed by this alone.** Until the reviewer is a separate strict agent on every code review, other reviewers keep the old behaviour. Paperclip still starts every review run in the author's worktree.
- **Repository-local config.** Plumbing tree-to-tree commands do not run external diff, textconv, fsmonitor or hooks, but git still reads `.git/config`. Option D removes this entirely; an isolated object-only clone is the middle path (U5).
- **Packager credentials.** Reading PR metadata needs a GitHub token on the Board side. Use a read-only, fine-grained token, never an agent's `GH_TOKEN`.
- **Package tampering.** Any agent process could edit the package before the reviewer reads it (same user). The checksums in the manifest catch accidental changes, not a determined writer. The relay re-verifies the head SHA.
- **Verdict path (U1).** Until it is solved, a human or the Board records the decision.
- **Cursor:** cannot be confined (OQ-033), so it is never used as `code-reviewer`.

## 6. Paperclip integration (no ADR-006 change)

| Need | Native Paperclip | Company OS (custom) |
|---|---|---|
| Review stage, participant, wake | `executionPolicy` review stage; assignment wake (OQ-035 gaps handled by the watchdog) | none |
| Reviewer agent | `claude_local`, engine `cli`, `extraArgs`: `--restricted --tools Read,Grep,Glob --strict-mcp-config --permission-mode dontAsk --permission-prompts none --settings <reviewer settings> --add-dir <Review Root>` | A new agent definition and profile; no `GH_TOKEN` bound |
| Run cwd | Always the issue's worktree (cannot change) | The reviewer is told to read the package; `Read(./**)` deny (U3) |
| Package build trigger | `provisionCommand` runs before each run with `PAPERCLIP_AGENT_ID` and `PAPERCLIP_ISSUE_ID` (U2: ordering, failure and timeout behaviour unverified; changing a project's workspace strategy is a production change) | Phase 1: a Board command (`pc.py review-pack <KEY>`). Phase 2: the review-wake watchdog builds before it wakes |
| Verdict | Run log API; issue decision API | Verdict Relay (U1) |
| Worktree lifecycle | Paperclip only | Never touched. The packager owns only `<Review Root>` |

ADR-006 holds:
- the packager creates no worktree, checkout or branch;
- it reads git objects;
- `<Review Root>` is not a Task Workspace;
- worktree creation and cleanup stay with Paperclip.

**Retention and cleanup.** The packager is the single owner of `<Review Root>`:
- it keeps every package of an issue until the issue is `done` or `cancelled`, plus 14 days (audit of what was reviewed);
- superseded heads are kept until then, read-only;
- it caps the total size of `<Review Root>` (default 2 GB), removing the oldest packages of closed issues first;
- it never deletes the package of an open issue;
- packages hold source code, so `<Review Root>` lives on the studio machine only and is never committed, synced or attached to issues.

## 7. Implementation phases

| Phase | Scope | Needs approval |
|---|---|---|
| 0 | This design | Board review of this document |
| 1 | Packager CLI (stdlib Python, like `pc.py`): build and validate from two SHAs in a given repository. Unit tests for paths, limits, binary, symlinks, collisions, staleness. Integrity test: `.git` and the worktree byte-identical before and after | No (offline, throwaway repository) |
| 2 | Strict reviewer on a package, outside Paperclip: repeat the OQ-042 experiment with the package. Test the `Read(./**)` deny (U3) and the verdict block format | No (sandbox) |
| 3 | GitHub check and PR lookup (`gh` read-only, Board token); fallback D | Token scope decision |
| 4 | Verdict recording experiment (U1) in a **sandbox Paperclip company** | Yes: start Paperclip; sandbox company |
| 5 | Trigger: `pc.py review-pack`, then the watchdog or `provisionCommand` (U2), in the sandbox company | Yes |
| 6 | Production: `code-reviewer` agent, profile, role text, review stages pointing to it, `sync-instructions` | Yes: new agent, configuration, ADR if roles or ADR-006 wording change |

## 8. Acceptance criteria

- [ ] The packager builds a package from pinned SHAs. `.git`, the Primary Checkout and every Task Workspace are byte-identical before and after (hash snapshot).
- [ ] Every validation rule in §4 has a test that refuses or omits as specified, including traversal, reserved names, ADS, collisions, symlinks, binary and oversize.
- [ ] A package is never used without `READY`, and never when the PR head no longer matches `headSha`.
- [ ] The strict reviewer finds the planted defects from the package alone, with correct `files/head` line references, and its toolset is `Read, Grep, Glob`.
- [ ] Repeated write, shell and git attempts by the reviewer all fail, and the package and the repository are unchanged.
- [ ] The verdict reaches the issue without the reviewer holding a shell or credentials (U1 resolved), in a sandbox Paperclip company.
- [ ] No step creates, moves or deletes a worktree or branch (ADR-006).
- [ ] Documentation states the remaining risks of §5. G-13 is not marked resolved by this work alone.

## 9. Unresolved questions

- **U1 Decision recording.** Can the stage decision be recorded without the reviewer making an API call itself? If not, is one narrowly allowlisted reporting call acceptable after its own bypass test?
- **U2 Trigger.** Does `provisionCommand` run before every run, synchronously, with a usable failure path? Or does the watchdog build first and let a run that finds no `READY` end without a decision (and is that run then retried or blocked by Paperclip)?
- **U3 Worktree reads.** Does a `Read(./**)` deny rule work while the cwd is the worktree, without breaking `--add-dir` reads?
- **U4 Limits.** Final values for `maxFiles`, `maxPatchBytes`, `maxFileBytes` and retention; per project or global.
- **U5 Untrusted repository config.** Is local plumbing with a null global and system config enough? Or must packages always come from an object-only clone or the GitHub API (option D)?
- **U6 Token.** Which GitHub token does the Board side use to read PR metadata?
- **U7 Cross-Task reads.** The fixed `--add-dir <Review Root>` lets a reviewer read other issues' packages. Is that acceptable, or should each run get its own folder (would need per-run `extraArgs`, which Paperclip does not offer)?

## Related documents
[../roadmap/open-questions.md](../roadmap/open-questions.md) (OQ-027, OQ-033, OQ-035, OQ-042) · [../architecture/stage1-gap-analysis.md](../architecture/stage1-gap-analysis.md) (G-13) · [../architecture/security-architecture.md](../architecture/security-architecture.md) · [../decisions/ADR-006-git-worktree-for-concurrent-tasks.md](../decisions/ADR-006-git-worktree-for-concurrent-tasks.md) · [../decisions/ADR-009-approval-before-merge.md](../decisions/ADR-009-approval-before-merge.md) · [../../knowledge/company/standards/task-contract.md](../../knowledge/company/standards/task-contract.md)

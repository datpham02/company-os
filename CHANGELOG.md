# Changelog

All notable changes to the Game Studio framework are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow Semantic Versioning; the current version is in [VERSION](VERSION).

## [Unreleased]

### Added
- OQ-042 Phase 6, P6-A (W1–W5; implementation only, nothing done in Soucean or Paperclip):
  - **W1:** `review-pack` through `pc.py` reads the issue and the task from Paperclip. It requires `in_review`, the right identity, and a project configured for the repository. Goal = title; acceptance criteria and write set only from exactly one `## Acceptance criteria` and one `## Write set` plain list (task-contract §2). Anything missing, ambiguous or not a list is refused, never inferred. No state or task file through `pc.py`; `--task-file` is refused there.
  - **W2:** reviewer profile and role. Profile `claude-reviewer-strict` and role `code-reviewer`; `config/paperclip/reviewer-settings.json`. `build-package.py --with-reviewer --staging-root --reviewer-cwd` builds it only on request and refuses a configuration that fails `check_reviewer_config`. That check now also requires `--strict-mcp-config`, `--no-session-persistence`, heartbeat off and `maxConcurrentRuns` 1. `post-import.py --resume` never resumes the reviewer.
  - **W3:** `pc.py create --review-package`: a `review` stage then an `approval` stage, both for `local-board`. Refuses `--review` (QA option a), a project without a configured repository, and a description without the task-contract sections.
  - **W4:** `pc.py review-run <KEY>` resumes the reviewer, runs `review-start`, waits for the run, and pauses it in `finally`, confirming the pause. It is refused while the reviewer has an active run or an open assigned issue (an earlier review's sub-issue could otherwise start a run on resume). `review-run --check` finds a reviewer left resumed.
  - **W5:** `docs/operations/review-package-runbook.md`; pilot variant in the `code-review-and-merge` and `development-cycle` workflows; SKILL.md; open questions OQ-044 (two consecutive `local-board` stages) and OQ-045 (adding one agent to the running company).
  - Offline tests: `test_review_github` (W1), `test_pc` (W1, W3, W4), `test_review_relay` (W2 checks, W4), `scripts/setup/test_build_package.py` and `test_post_import.py` (W2). Live behaviour is not verified (P6-B to P6-D).
- OQ-042 Phase 6 production proposal (`docs/design/review-package-phase6-proposal.md`, `PROPOSED`, authorizes nothing):
  - a strict `code-reviewer` agent in Soucean, profile `claude-reviewer-strict` (as validated in R1, P0 and R5), paused between reviews, no secrets;
  - a pilot on `soucean-game` for five Tasks with a `review` stage for `local-board` filled by the relay;
  - runbook outline, tokens, roots and retention, named risks (G-13 open, G-14 and B5 accepted, F1 window, B1 open items);
  - work items W1–W5 and rollout steps P6-A to P6-D, each needing its own approval.
- OQ-042 R6 Board decisions (2026-11-21):
  - **B3 / V3 answered: yes.** A sandbox agent's own process read every company on the instance, `SOU` included, with one `curl` and no credentials (`local_trusted`), so G-14 is a real gap.
  - **B4 (G-14)** is accepted as a named risk for now; the authenticated-mode migration (OQ-043, A5) stays planned.
  - **B5** is accepted as a named risk.
  - **B6:** the Paperclip version re-check list is drafted (R6 §8) for the Board's review.
- OQ-042 R5 live evidence (`docs/design/review-package-r5-results.md`, sandbox OPT, soucean-game sandbox PRs and a throwaway repository): §12 criteria 1, 3, 4, 7, 8 and the Board merge after an approved relay verified live; criterion 2 for representative cases; B5 confirmed (the owner's login bypasses branch protection). **Finding F1:** the relay overrode a decision the Board made by hand while it ran (test 6b failed), new R6 blocker B7. Design §12 and the R6 assessment updated. F1 was then fixed in PR #64; the 6b re-run passed live and B7 is recorded as closed (narrowed).
- OQ-042 R6, Phase 6 readiness assessment (`docs/design/review-package-r6-phase6-readiness.md`, review only): **not ready**. Blockers B1–B6: R5 live evidence and the untested merge; `--cleanup` closure from Paperclip; V3; G-14; the ADR-022 branch-protection question; Paperclip version re-check list. Also lists what the Phase 6 proposal must contain and the recommended order.
- Credential log mitigations (after the GH_TOKEN log redaction probe):
  - a credential rule for every agent: `rules.secrets` appended to both Claude profiles, a `## Credentials` section in all 8 role files, and Studio Rules R4.1 extended;
  - an environment-dump deny list in both Claude profiles' `disallowedTools` (`printenv`, `env`, `set`, `gh auth`, `git credential`, commands expanding `GH_TOKEN`/`GITHUB_TOKEN`/`PAPERCLIP_API_KEY`, and others).
  Cursor agents get only the rule. Applied to the live Soucean agents on 2026-11-21 (AGENTS.md section on all 8, Claude `extraArgs` on 6). Verified the same day: in a sandbox run the rule stopped the agent from trying any environment dump, and the Claude Code CLI refused all 8 dump commands under the deny list alone, while bare-name commands still ran.
- GH_TOKEN log redaction probe (`docs/design/gh-token-log-redaction-probe.md`, sandbox OPT, fake value): Paperclip 2026.1023.0 does not redact an `env` secret in run logs. A command that prints `GH_TOKEN` stores the value in plain text in the run log file, the log API and the run detail; only the `adapter.invoke` event hides it. ADR-022 updated; mitigations left to the Board.
- ADR-022 (Accepted, R4 of the Review Package roadmap): in Review Package sandboxes the author only pushes and the Board opens the PR, with no new credential; production code-writing agents open their own PRs with one shared fine-grained `GH_TOKEN` (Contents and Pull requests read/write, at most 90 days, no admin, workflow or delete scope) bound as a Paperclip secret reference, never to read-only agents. Each agent clone must use `gh` with the token instead of the host's Git Credential Manager login (the `soucean-game` clone was fixed on 2026-11-21). A full-permission shared token was considered and rejected. The Board chose *All repositories* on its own account and accepted the risk: the token acts as the owner, so branch protection probably does not bind it (unverified), and the merge gate is procedural for agent tokens.
- OQ-042 R3, hand-over runs in `pc.py show`: Paperclip 2026.1023.0 cancels the run of an agent that moves its own issue to someone else (`errorCode: issue_reassigned`). `show` now labels such a run "handed over" when its run record (`GET /heartbeat-runs/<id>`) confirms `reassignmentStopConfirmed` and `cancellation.expected`; any other cancellation shows its reason, for example `cancelled (agent_paused)`. Display only; the relay rules are unchanged. 3 new tests.
- OQ-042 R2, Paperclip-backed `--unstage` (`docs/design/review-package-r2-unstage-design.md`): `review-pack --unstage` through `pc.py` decides from Paperclip, not the state file: every run of the `code-reviewer` agent since staging (`GET /companies/<id>/heartbeat-runs?agentId=`) and the lock's run by id. Active runs refuse even with `--abandon`; `interrupted`, unknown statuses, mismatches and Paperclip errors refuse unless `--abandon` (audited as unverified). `unstage` takes `staging.op`, checks twice around an `unstaging` mark and deletes the lock last; `review-start` records `companyId` and `reviewerAgentId` in the lock and refuses a lock marked `unstaging`. `review_pack.py` stays network-free (the check is injected). `--status` still reads the state file (follow-up). Offline tests; the live check (R2-E) needs approval.
- OQ-042 reviewer write isolation (P0, `docs/design/review-package-reviewer-write-isolation.md`): Paperclip 2026.1023.0 adds its write-capable MCP tools to every issue-scoped `claude_local` run. The reviewer profile now removes every MCP tool (`--disallowedTools mcp__*` and a settings deny `mcp__*`) on top of `dontAsk` with an allow list of Read, Grep, Glob; `review-start` refuses a reviewer without that profile, any `env`, or a forbidden flag; `review-relay` reads the whole run log and accepts it only if its size and SHA-256 equal Paperclip's recorded `logBytes`/`logSha256` for the lock's run (it previously read only the first 256 KB page), then refuses a run whose log offered any tool besides Read, Grep, Glob, used another tool or recorded a refused attempt. New opt-in `probe_reviewer_tools.py` re-checks Claude Code's behaviour locally. Offline tests only; the sandbox step needs Board approval. G-13 stays open.
- OQ-042 Option B, reviewer run binding (post-Phase 5 assessment §3.5): `pc.py review-start <KEY>` creates one review sub-issue per staging (child of the issue, assigned to `code-reviewer`, backlog, no project) and wakes the reviewer on demand for it; each staging gets a random `reviewId` and `challenge` in `current/REVIEW-ID.txt` only; `review-relay` accepts only the recorded run of that sub-issue and a verdict echoing both values, and closes the sub-issue after a decision. The company-scoped run path of Phase 4b is removed. `review-start` records its progress in the lock and recovers an interrupted start without a second sub-issue or wake, failing closed when an earlier request's outcome is unknown; `staging.op` serializes it with `unstage`. Offline tests only; not yet run live. G-13 stays open.
- OQ-042 Review Package Phase 5, sandbox end-to-end (2026-11-21) in a throwaway company on the live instance with `datpham02/soucean-game` (Board-approved): Author Task to PR, GitHub-API package, strict company-scoped review, relay decision, duplicate, stale-head and other refusals, manual fallback, unstage and cleanup. The author could not open the PR without a `gh` credential (the Board side did). The Board closed the PR without merge; §12 partly met. Record `docs/design/review-package-phase5-sandbox.md`. G-13 stays open.
- OQ-042 Review Package Phase 4b, live relay test (2026-11-21) in a throwaway company on the live instance: V1 confirmed (user review-stage participant; the relay recorded a decision), V2 refuted (Paperclip cancels an issue-scoped run of a non-assignee agent), V3 not tested. `review-relay` now also accepts a `code-reviewer` run woken without an issue, if it belongs to the issue's company and to no other issue. G-13 stays open.
- OQ-042 Review Package Phase 4a, Verdict Relay (`pc.py review-relay <KEY> --run-id R`, `scripts/review_relay.py`):
  - checks the issue is `in_review` with the relay identity as active participant, the run is a succeeded `code-reviewer` run started after staging, the staged package verifies, the PR head is unchanged, and the run's final message holds exactly one valid verdict whose findings point into the package;
  - posts the findings with a `relay-receipt`, then records the decision; re-runs never duplicate; 5xx/network errors get 3 attempts; a 4xx keeps the comment, is audited as `relay-refused` and leaves the Board fallback.

  55 new tests against a fake Paperclip. **Not yet run against Paperclip:** the sandbox validation (V1–V3) needs Board approval. G-13 stays open.
- OQ-042 Review Package Phase 3, GitHub source (`review-pack <KEY> --github-pr N --github-repo o/r --task-file T`, `scripts/review_github.py`):
  - reads a pull request over the GitHub REST API with the packager's read-only token from Windows Credential Manager;
  - reads every page of the file list and the trees at head and at the merge base;
  - every blob's git id is recomputed by the packager; a moved head, a truncated tree, a missing blob, a submodule change or a short file list are refused;
  - the token is never logged (errors redacted); 401/403 refuse with no fallback; a warning under 14 days to expiry.

  25 new tests with an in-memory fake GitHub. **Not yet run against GitHub:** that needs a throwaway repository and a token created by the Board. G-13 stays open.
- OQ-042 Phase 1 review packager (`pc.py review-pack`, `scripts/review_pack.py`), built from fixture files only. It does not use git, GitHub, Paperclip or a token.
  - Immutable `store/<KEY>/<head>/` packages: manifest with SHA-256, atomic build with `READY` last, reuse of intact packages.
  - Every §5.2 limit and §5.3 validation rule enforced fail-closed.
  - One-review-at-a-time staging under an exclusive lock, with `--status`, `--unstage` and `--abandon`.
  - Retention cleanup with a 2 GB cap and two-step deletion.
  - An append-only JSONL audit log.
  - 62 new tests.
  The design stays `PROPOSED`; G-13 stays unresolved.
- Write Set conflict guard in the Paperclip skill's `release` (task-contract.md §4.1, E1): every release compares the issue's Write Set with every unmerged issue of the same project (including `done` issues whose merge Paperclip has not seen) and refuses on overlap, listing issues and paths. `--force` no longer skips the Write Set check. Tests in `.claude/skills/paperclip/scripts/test_pc.py`.
- WIP limit in the Paperclip skill (task-contract.md §5, E2): `release` refuses an issue whose assignee already has an `in_progress` issue in any project of the company, including one released earlier in the same command, and `--force` no longer skips this; `triage` reports breaches from the same calculation and says when WIP could not be checked. `maxConcurrentRuns` is unchanged (OQ-041).
- Start gate in the Paperclip skill (P0.3): only `release` starts a task. `create` always creates in `backlog` (`--status todo` refused); `assign` never changes a `backlog` issue's status, refuses `--status todo`, and hands over a started issue only with `--status backlog`; `comment` refuses an agent-assigned `backlog` issue and `wake --issue` a `backlog` issue, since Paperclip wakes the agent on both. Paperclip UI, MCP `create_task` and agents' direct API paths are not covered.
- Reviewer isolation re-audit (P1.1, G-13): a source audit of Paperclip 2026.1023.0 and its adapters found no supported way to keep a reviewer out of the author's worktree and branch. G-13 stays unresolved; findings and options are in OQ-042, OQ-002, OQ-033 and security-architecture §4. Task contract §8 and the `qa` role text now say the review runs in the author's workspace (`qa` is no longer told to check out the branch there). No configuration changed.
- OQ-042 experiment (2026-11-20): a dedicated Claude Code reviewer tested on native Windows outside Paperclip, in a throwaway repository. With read-only tools and a diff supplied from outside it reviewed correctly and every write was refused. With git read commands allowed through Bash, `git diff/log/show --output=<file>` wrote files inside and outside the repository. OQ-042 stays open, and G-13 stays unresolved. No configuration changed.
- Review package design (`docs/design/review-package.md`, `PROPOSED`) for the OQ-042 diff handoff, revised with the Board decisions U1, U2, U4, U5, U6 and U7:
  - a Board-side Verdict Relay with a human fallback. Paperclip records a stage decision only from the active stage participant, so the relay can record it only when its identity is that participant (proposed: the Board Operator user, with `code-reviewer` advisory). Otherwise the Board Operator records the decision manually. The participant arrangement and API compatibility still need sandbox validation (V1–V3);
  - a manual `pc.py review-pack` trigger;
  - the approved limits and retention;
  - the GitHub API as the first source, never a working repository;
  - a dedicated read-only packager token;
  - per-head storage with one serialized staging folder.
  Recorded the finding that Paperclip accepts a stage decision only from the current participant. Documentation only; nothing implemented, G-13 unresolved.

### Changed
- `review-pack --status` through `pc.py` now reports the reviewer's runs from Paperclip (the same check as `--unstage`: `source: paperclip`, `verified`, `active`, runs), never prints the staging challenge, and falls back to the state file only outside `pc.py`. Refusals of `--unstage` and `--status` are audited with the staged issue instead of `issue: null`.

### Fixed
- `review-relay` could override a decision the Board made by hand while the relay ran (R5 finding F1, R6 blocker B7): its decision PATCH was unconditional and it writes as `local-board`. It now reads the issue again just before the PATCH and refuses (audited `relay-refused`, the findings comment stays) if the status, stage participant, stage or last decision changed since its checks. Paperclip 2026.1023.0 has no conditional status update (`expectedExecutionPolicy` covers policy-only writes), so the remaining window between that read and the PATCH is narrowed, not closed. 4 new tests, which fail on the previous code; live re-run of R5 test 6b in sandbox OPT passed (`OPT-17`: relay refused, the Board's decision stood).
- `review-pack --cleanup` and the 2 GB cap cleanup (R6 blocker B2): through `pc.py` they decided closure from the Phase 1 state file, which no longer tracks Paperclip. They now read each package issue's status and closing time from Paperclip (`completedAt` for `done`, `cancelledAt` for `cancelled`; Paperclip has no `closedAt`) and fail closed: an unanswered read, another issue's record, an unknown status or a missing closing time keeps the package and is audited as `cleanup-skipped`. One Paperclip read per issue per command. Outside `pc.py` the state file is still used. 5 new tests, which fail on the previous code.
- `review-relay` and `review-start` (A3): a Paperclip failure in the check phase (network or 5xx after the retries, a 4xx such as an unknown issue, or a failed reviewer lookup) escaped as a raw exception with no audit line. Every failure before anything is recorded is now an audited `refuse` with the Board fallback. A failed `relay` audit write after the decision was recorded no longer reports "Nothing was recorded": the relay succeeds with a warning, and a failed `relay-refused` audit write no longer turns a recording refusal into "Nothing was recorded". 6 new tests, which fail on the previous code.
- R2 `--unstage` (self-review): `reviewer_run_state` ignored reviewer runs created before the staging time even when they were still active, although such a run can read staging through the agent's fixed `--add-dir`. Any active run now blocks, whenever it started; the staging time still limits which `interrupted` or unknown runs count. Regression test added. The no-lock orphan cleanup now states that the reviewer's runs cannot be checked without a lock.
- Review packager audit (2026-11-20), regression tests for each fix:
  - **D1:** a junction or symlink planted under the Review or Staging Root made the packager write or delete outside its roots (verified on Windows 11). It now refuses any link below its roots and in packages.
  - **D3:** names shaped like 8.3 short names (for example `LONGFI~1.CS`) could alias another file. They are now refused.
  - **D2:** `CON .txt`-style device names are now refused as well.
  - **D4:** manifest paths are re-validated before verification.
  - **D5:** two builds of the same issue could delete each other's temporary folder. There is now a per-issue build lock, with stale takeover after 60 minutes.
  - **D6:** filesystem errors surfaced as raw exceptions without an audit entry. They are now logged refusals.
  - **D7:** a damaged audit line crashed `--status` and `--unstage`. It is now refused with a message.
  - **D8:** Task text in `REVIEW.md` came before the instructions and could pose as them. It is now quoted after them, inside a safe fence.
- The Paperclip skill read only the first page (500) of the paginated issue list. `release`, the Write Set guard and `triage` now read every page with the keyset cursor and refuse to act on a partial list.
- Reviewers editing the author's branch (SOU-2 commit db51e6d, SOU-18 commit e7e3f88, both by `web-engineer` on Cursor): the task-contract rule was not in any role text. All eight role files now forbid a reviewer from editing, committing, rebasing or pushing the author's branch, and the `git` rule in `config/paperclip/agents.json` says only the assignee commits and pushes. Gap G-13.

### Added
- ADR-021: backend is Laravel + MySQL (no Supabase); Laravel Reverb for event-driven real-time, a dedicated server per fast-paced game; everything local in a Docker Compose stack until hosting is decided (candidate Vietnix VPS). Contract, Web production rules, `web-engineer` role, OQ-036/037 and the dependency registry (Docker Desktop) updated; QA may run `docker compose run --rm test`.
- Game platform contract version 1 (ADR-020): the Board-approved GAM-16 design (adapter, mount, embedding, manifest, host behaviour, identity, names, server-side validation, weekly boards, data, credentials) recorded in `knowledge/company/shared/game-platform-contract.md`, replacing the placeholder. The backend part of D4 is decided in ADR-021.

### Added
- `scripts/setup/sync-instructions.py`: pushes role texts from Git into a live Paperclip company (OQ-040). Used on 2026-11-05 after the M1 restructure; `Game Director` renamed `Director` in Soucean; old company `GAM` archived after its open work moved to SOU-1..SOU-10.

### Changed
- **Restructure into `knowledge/` and departments (ADR-019, migration map step M1).** Moved with `scripts/maintenance/move-files.py` (mapping in `scripts/maintenance/m1-moves.json`, links rewritten):
  - `company/` → `knowledge/company/` (`RULES.md` → `policies/rules.md`); `workflows/` → `knowledge/company/workflows/`;
  - shared roles → `knowledge/company/agents/`; game roles → `knowledge/departments/game/agents/`; `web-engineer` → `knowledge/departments/web/agents/`;
  - `projects/` → `knowledge/projects/` (`project-registry.yaml` → `registry.yaml`);
  - `task-contract.md` → `knowledge/company/standards/`, `provider-allocation.md` → `knowledge/company/policies/`, `game-platform-contract.md` → `knowledge/company/shared/`;
  - `docs/glossary.md` → `docs/vision/terminology.md`; `open-questions.md` and `implementation-roadmap.md` → `docs/roadmap/`; `studio-bootstrap.md` → `company-bootstrap.md`.
- `game-director` is renamed **`director`**, the company-wide director and Paperclip root for every department.
- Split: `COMPANY.md` (company mission; game values to the Game charter), `ORGANIZATION.md` (scopes, live providers), rules R1.4–R1.6 and R7.1, `project-initialization.md` (company workflow plus the game concept workflow), `company-design.md`, `security-architecture.md` §10 (principle stays; platform rules to the Web department).
- Project registry entries have `department` and `contributingDepartments`; `config/paperclip/agents.json` has `department` per agent; the package builder reads the new tree and rejects duplicate slugs.

### Added
- Department charters (`knowledge/departments/game/`, `knowledge/departments/web/`), `game-rules.md`, `new-game-concept.md`, `production-environments.md`, knowledge indexes and project entrypoints; ADR-019.
- Task contract, WIP limit, blocker protocol and liveness rules (`docs/design/task-contract.md`, ADR-017 proposed), the daily triage workflow (`workflows/daily-triage.md`), and a `## Task hygiene` section in every role file.
- Provider allocation rule for any number of AI providers (`docs/design/provider-allocation.md`, `config/providers.example.yaml`, ADR-015 proposed) and `allocation` metadata in role files.
- Studio bootstrap procedure for importing pre-configured agents (`docs/operations/studio-bootstrap.md`, ADR-016 proposed); open questions OQ-040, OQ-041; gaps G-11, G-12.
- `scripts/setup/build-package.py`, `scripts/setup/post-import.py` and `config/paperclip/agents.json`: build a clean Paperclip package with full agent configuration and finish an import. Used on 2026-11-05 to create the company **Soucean** (`SOU`); the old company `GAM` is paused as an archive.
- ADR-018 (accepted): the repository is renamed `datpham02/company-os`.
- Paperclip skill: read-only `triage` command; `release` now checks write set, review/approval stages, open blockers and WIP (`--force` to override).
- `runtime/tools/review-wake-watchdog.ts`: first Stage 2 gap filler. It wakes reviewer agents that Paperclip leaves idle after an in-run hand-off (OQ-035).
- `docs/architecture/stage1-gap-analysis.md`.
- `.claude/skills/paperclip`: Claude Code skill and stdlib Python CLI (`pc.py`) for running Paperclip from chat as the Board Operator.
- `runtime/tools/start-studio.cmd`: one-click start of Paperclip, the review watchdog and the UI; skips anything already running.

### Changed
- `agents/qa` declares `slug: qa-engineer` so imports match the live Paperclip agent instead of creating a second one.
- Parallel-task, delegation and failure workflows check overlap against every unmerged Task, use blocker relations, and handle cancelled blockers and stalled reviews.
- Paperclip now runs as a global, pinned install (`paperclipai run` from `~/game-studio-workspace`) instead of `npx`, so `npm_*` variables no longer leak into agents (OQ-034).

### Changed
- ADR-013: the studio machine is now the Board Operator's Windows 11 computer. ADR-013 supersedes ADR-003 (native Ubuntu). `docs/operations/ubuntu-setup.md` is replaced by `windows-setup.md`, and Linux-specific guidance (systemd, Unix permissions, paths) is rewritten for Windows.
- Dependency registry: versions re-verified on the Windows machine (Claude Code 2.1.316, GitHub CLI 2.97.0). Codex and OpenSpec are not installed there.
- Cursor CLI added as a third execution provider (registry `cursor-cli`, `docs/integrations/cursor-integration.md`, OQ-033).
- Open questions: added OQ-031 (Paperclip on native Windows) and OQ-032 (Codex sandbox and `process` shell on Windows); OQ-028 resolved.

## [0.1.0] — 2026-11-03

### Added
- Documentation system v1.0: architecture, design, ADRs (ADR-001 to ADR-012), workflows, integrations, operations, and guides.
- Studio definition: `company/` and seven agent role definitions in `agents/`.
- Project registry (empty) and project configuration schema (`PROPOSED`) in `projects/`.
- External dependency registry with candidate dependencies in `dependencies/registry.yaml`.
- `AGENTS.md` and `CLAUDE.md` so the repository works with both Codex and Claude Code.

### Notes
- No Runtime code exists. All Runtime behavior is `PLANNED`.
- Paperclip capabilities were verified against Paperclip's repository documentation at commit `7b8aa60` (2026-11-03). Unverified items are tracked in `docs/architecture/open-questions.md`.

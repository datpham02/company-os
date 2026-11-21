# Implementation Plan: Company OS Roadmap, Phase 1 to Phase 4

- **Status:** Stage A deliverable; **approved for Stage B by the Board Operator on 2026-11-21** with the decisions recorded in §10. Live actions still need their own authorization. Stage B starts only after the Board explicitly approves this plan, and every live action listed as BLOCKED needs its own authorization.
- **Canonical roadmap:** [phases.md](phases.md) (`PROPOSED`, Phases 0–4). Phase names, order and scope below follow it.
- **Inspected:** `main` at `027825b` (2026-11-21). Working tree clean. Branch for this deliverable: `docs/roadmap-stage-a`, not committed.
- **Companion deliverable:** [stage1-gap-analysis.md](../architecture/stage1-gap-analysis.md). Its two new sections are the MUST-by-MUST matrix (Phase 1 item 5) and the Task evidence ledger (Phase 1 item 4).
- **Not the same thing:** the Review Package phases 1–6 (OQ-042) are a separate track. Review Package P6-A is merged (PR #68); P6-B, P6-C and P6-D are not authorized. Nothing here authorizes them, and their approvals authorize nothing here.

## 1. Executive status

| Phase | Status | Confidence | Evidence |
|---|---|---|---|
| 0 Environment and verification | **Done**, except 0.2 and 0.7, which are partial on the Codex side | High | §2 |
| 1 Stage 1 studio | **Substantially done; not yet closed.** Items 1–4 are met in substance. Item 5 (gap analysis) now has its matrix (draft, this Stage A). Document drift and three Board decisions remain | High for items 3–5, medium for item 1 (the trial-Task step is not evidenced) | §3 |
| 2 Lightweight tooling | Not started. Two candidates are justified by Phase 1 evidence, one more needs a decision, and two are not justified | Medium | §4 |
| 3 Runtime (Stage 2) | Not started. **No verified gap that a process-adapter Runtime closes better than configuration or existing tooling.** Recommendation: do not build now | Medium | §5 |
| 4 Hardening | Not started. Four areas planned around the verified risks G-14, B5 and Cursor isolation | Medium | §6 |

- **Execution starts at Phase 1.** Phase 0 is not repeated. Two Phase 0 items are left partial on purpose (Codex), with a decision (D-09).
- **Main uncertainty:** the Board decisions D-01 to D-09 (§10). Most remaining Phase 1 work is register and document fixes, done in the repository; the few live checks are listed as BLOCKED.

## 2. Phase 0 evidence ledger

| # | Item | Evidence | Status | Revalidate? |
|---|---|---|---|---|
| 0.1 | Repository under Git and pushed | OQ-028 resolved; ADR-018 renamed the repository to `datpham02/company-os` (2026-11-05) | DONE | No. Wording in phases.md and OQ-028 still says `game-studio` (P1-T03) |
| 0.2 | Codex CLI install, login, `codex exec` probe | OQ-009 resolved (`codex-cli 0.166.0`, 2026-11-03); OQ-010 partial: the `codex exec` test failed ("Quota exceeded") | PARTIAL | Only if Codex becomes a provider (D-09) |
| 0.3 | Paperclip on Windows, `local_trusted`, pinned | OQ-031: 2026.1023.0 on `127.0.0.1:3100`, `local_trusted`, 2026-11-03; global install (OQ-034); still the installed version | DONE in practice | Register fix: OQ-008 and OQ-024 never updated, OQ-024 still says "not installed" (P1-T03) |
| 0.4 | Scratch company and Game Repository | "Scratch Lab", project `scratch-game`, prefix `SCR` (OQ-002, OQ-003, OQ-004); a local repository, not a private GitHub one | DONE (indirect) | No |
| 0.5 | `process` agent environment | OQ-003 resolved: no Task ID, wake reason or workspace injected; OQ-032: full Git Bash path needed | DONE | No |
| 0.6 | Isolated `git_worktree`, two concurrent Tasks | OQ-002, OQ-004, OQ-030; cleanup explained from source only; `branchTemplate` untested | DONE (cleanup partial) | After any Paperclip upgrade (ADR-011) |
| 0.7 | Claude Code and Codex headless per profile | OQ-011 resolved for `claude_local`; the Codex part was never run; C-002 open | PARTIAL | Only with D-09 |
| 0.8 | `qa` review plus Board approval policy | OQ-005: works on the Paperclip side; no GitHub link. The summary table and the entry disagree | DONE (Paperclip side) | No (P1-T03 fixes the table) |
| 0.9 | `company import` preview | OQ-007 resolved; later OQ-040 found `--collision replace` refused; ADR-016 added clean package builds | DONE | No (ADR-012 still names `--collision replace`; recorded, not edited, P1-T03) |
| 0.10 | ADR-011 and ADR-012 | Both Accepted 2026-11-03 | DONE | No |

Exit criteria hold: the results are in open-questions.md, apart from the register gaps P1-T03 fixes, and both ADRs are accepted.

## 3. Phase 1 plan (Stage 1 studio)

### 3.1 Item by item

| Item | Requirement | Actual status | What remains |
|---|---|---|---|
| 1 Company and agents | "The 7 Agent Instances" via agent-onboarding | Live company **Soucean** (`SOU`) with **8** agents, created by package import (2026-11-05, ADR-016). The earlier company `GAM` is **archived** in Paperclip; some docs still say "paused". The hire-request path was replaced by import (company-bootstrap.md). No record of the per-agent trial Task or of a Test Environment pass for every Soucean agent | P1-T01 (roster wording, D-01), P1-T02 (onboarding evidence, D-02) |
| 2 Token and branch protection | security-operations.md §1–2 | `GH_TOKEN` as a company secret, bound only to the 5 code-writing agents (version 2, 2026-11-21); both project repositories have `main` protected (PR, 1 approval, no force-push, no deletion). Deviations: the token covers *All repositories* (accepted, ADR-022); the §2 step "rejected when pushing to the protected Default Branch" fails for the owner account (B5, accepted); the repositories are public, a deliberate choice recorded in each project's README, while security-operations.md §1 defaults to private | P1-T04 (align security-operations.md with ADR-022) |
| 3 First Game Project | project-initialization contract | `lamplight-vigil` registered and set `active` on 2026-11-04 (GAM-1 concept, GAM-2 seed, GAM-5 vision, GAM-7 milestone); v0.1.0 released. Gaps:<ul><li>the registry entry has no explicit `type`;</li><li>the registry PRs were written in the Board's session, not by `producer`;</li><li>the repository is public;</li><li>`soucean-game` (platform) was still `initializing`.</li></ul>The registry's `qa` is correct: it is the role's Agent ID (`qa-engineer` in Paperclip, ORGANIZATION.md); the Stage A survey flagged it wrongly | P1-T06 (registry conformance, D-03) |
| 4 5–10 real Tasks | development-cycle and code-review-and-merge | **Met.** Task ledger: 49 Tasks with a merged PR, 38 with the whole chain (stages, reviewer comment, Board comment, Board merge). Deviations: GAM-20 and GAM-44 merged before `done`; GAM-22 no stages; nine `qa-engineer` reviews without a reviewer comment | Recorded in the gap analysis; no new Tasks needed |
| 5 Gap analysis | Every MUST of ADR-006, ADR-009, rules.md, runtime-architecture.md | The file existed with gaps G-1 to G-14 but no MUST matrix. Stage A added the matrix. **Summary:** PASS 4, GAP 3 (one accepted), PARTIAL most, NOT VERIFIED 6 behavioural, runtime items marked Stage 2 | P1-T07 (Board review of the matrix), P1-T08 to P1-T10 (repository-local follow-ups) |

### 3.2 Tasks

| ID | Task | Kind | Depends on | Acceptance | Effort |
|---|---|---|---|---|---|
| P1-T01 | Update the roster wording: phases.md item 1 "7 Agent Instances", agent-onboarding.md, and the GAM status ("archived", not "paused") in ADR-018 context docs and CHANGELOG notes | Repo docs | D-01 | Docs match `config/paperclip/agents.json` and the live roster read; no Accepted ADR edited (notes go to open-questions.md or a superseding record) | S |
| P1-T02 | Record agent onboarding evidence: Test Environment result per Soucean agent and the trial-Task step, or record the Board's decision that the import path replaces it | Live (BLOCKED) or Board decision | D-02 | Either eight recorded Test Environment passes (live run, needs authorization) or a recorded decision | S |
| P1-T03 | Register fixes in open-questions.md and dependencies/registry.yaml: <ul><li>OQ-008, OQ-024 (installed, pinned);</li><li>OQ-028 wording (renamed repository);</li><li>OQ-005 and OQ-017 summary rows that disagree with their entries;</li><li>OQ-010 and Codex status in provider-allocation.md and codex-integration.md (installed, `exec` not working);</li><li>the ADR-012 note on `--collision replace` (recorded in OQ-040, ADR untouched);</li><li>the registry's Paperclip notes ("not yet installed");</li><li>the Claude Code verified version;</li><li>autonomous-execution-log "G-1 to G-13"</li></ul> | Repo docs | — | Every listed contradiction resolved or explicitly noted; `git diff --check` clean | S |
| P1-T04 | Align security-operations.md §2 with ADR-022: token scope *All repositories* as an accepted risk; §2.3 rejection test known to fail for the owner account (B5); rotation reminder; the Review Package packager token | Repo docs | — | No contradiction with ADR-022 or security-architecture.md | S |
| P1-T05 | Record the run-log retention Paperclip actually applies (ADR009-5), from source reading, plus the backup retention already observed | Repo docs (read-only source reading) | — | Retention stated with source references, or marked `UNVERIFIED` and added to open-questions.md | S |
| P1-T06 | Registry conformance for `lamplight-vigil` and `soucean-game`: <ul><li>add `type`;</li><li>record the registry-PR author deviation;</li><li>mark `soucean-game` `active` only if the Board confirms its initialization is finished</li></ul> | Repo docs + D-03 | D-03 | Registry entries match the schema (`project-config.schema.yaml`) and the live slugs | S |
| P1-T07 | Board review of the MUST matrix and the Task ledger (Stage A drafts); fix any finding | Board | P1-T01…T06 | The Board accepts the matrix, or comments that P1-T07 resolves | S |
| P1-T08 | Proposal for R4.2 / R4.3: narrow `Bash(cat *)` and `npm run *` in the Claude profiles, or record the risk | Repo config proposal; live apply BLOCKED | D-04 | Offline build check passes (`build-package.py`); live apply only with authorization | M |
| P1-T09 | Proposal for R2.8 / G-9: whether agents keep `mcp__Paperclip_projects` task creation | Repo config proposal; live apply BLOCKED | D-06 | As P1-T08 | S |
| P1-T10 | Proposal for X-4 / R1.4–R1.5: protect `main` of `datpham02/company-os`, or record the risk | GitHub setting change (BLOCKED) | D-07 | Board decision recorded; setting changed only with authorization | S |
| P1-G | Phase 1 gate report | Report | P1-T01…T10 | §11 Phase 1 gate | S |

## 4. Phase 2 plan (lightweight tooling, conditional)

| Candidate | Phase 1 evidence | Already provided? | Cost | Decision |
|---|---|---|---|---|
| `scripts/validate-registries` | The schema exists but nothing enforces it; cross-references (agent IDs to role files, project repositories to `config/paperclip/agents.json`, dependency IDs) are checked by hand. Phase 1 found only small drift (missing `type`, a stale status). The validator prevents drift rather than fixing a recorded incident (`project-config.schema.yaml`: "validation script is PLANNED") | No | Small, read-only, no credentials | **BUILD** (P2-T01) |
| `scripts/check-dependencies` | Drift in `dependencies/registry.yaml`: Paperclip "not yet installed" notes, Codex "pending", the Claude Code verified version behind the one in use. ADR-007 says drift must be checked | No | Small. It runs `--version` commands locally, read-only | **BUILD** (P2-T02) |
| `scripts/generate-company-package` | OQ-007 resolved: no generated package needed for import; the clean build exists | **Yes:** `scripts/setup/build-package.py` (IMPLEMENTED) | — | **DO NOT BUILD** |
| Agent configuration drift check (the G-11 "Phase 2 tooling candidate"; not in the original list) | 2026-11-21: `qa-engineer`'s live AGENTS.md had drifted from `main` unnoticed; `extraArgs` had to be compared with a build by hand, twice | Partly: `sync-instructions.py --dry-run` covers role texts only | Small, read-only Paperclip reads | **NEEDS DECISION** (D-10; recommended BUILD, P2-T03) |
| Write-set check of the files a Task actually changed (R2.6; not in the original list) | Overlap is checked only at release; no Task is recorded as having changed files outside its write set (G-10 concerned a shared worktree, not the write set) | Partly: reviewers check scope; the release guard | Medium (needs per-PR diffs) | **DO NOT BUILD now.** Reconsider if a write-set violation is recorded |
| `templates/game-project/` | Two projects so far; no seeding error recorded; OQ-018 open | No | Small, but it goes stale without use | **DO NOT BUILD now.** Reconsider when the next Game Project is approved |

### 4.1 Tasks (justified tools only)

| ID | Design | Tests | Acceptance | Effort |
|---|---|---|---|---|
| P2-T01 `scripts/maintenance/validate-registries.py` | Stdlib only. Checks: <ul><li>`knowledge/projects/registry.yaml` against the required fields and enums of `project-config.schema.yaml`;</li><li>agent slugs against `config/paperclip/agents.json`;</li><li>dependency IDs against `dependencies/registry.yaml`;</li><li>project repositories against `agents.json` projects.</li></ul> Exit 1 with a list of findings. Read-only | Offline unittest with fixture files: a valid registry, each error kind, malformed YAML | Passes on the corrected registry (after P1-T06); each error kind is caught | S–M (a stdlib YAML subset reader is needed: no PyYAML, TO CONFIRM) |
| P2-T02 `scripts/maintenance/check-dependencies.py` | For entries with a version command, compare the local version with `verifiedVersion`. Report only; never installs | Offline unittest with a fake command runner; one manual local run | Reports the current drift correctly; no network, no writes | S |
| P2-T03 (if D-10) `scripts/setup/check-agent-drift.py` | Read-only. Compares each live agent's `adapterConfig.extraArgs`, `runtimeConfig` and AGENTS.md with what `build-package.py` would produce (same logic as `sync-instructions.py --dry-run`). Never writes | Offline unittest with a fake Paperclip; read-only live run | Detects the kinds of drift seen on 2026-11-21 | M |

## 5. Phase 3 plan (Runtime, conditional)

ADR-011: Stage 1 uses Paperclip's own adapters and Paperclip-owned worktrees; a Runtime is built only for verified gaps, through the `process` adapter. Component by component:

| Component | Verified gap it would close | Paperclip or tooling already covers it? | Decision |
|---|---|---|---|
| 1 Config loader + schema | None on its own; it exists only to serve components 2–6 | — | **Do not build** (no consumer) |
| 2 Dispatcher + Paperclip client | G-8 (agents cannot read other issues), G-12 (WIP across all paths) | G-8: a read-only helper is proposed, but it needs G-14 fixed first. G-12: the `release` guard covers the Board path; the remaining bypasses are Paperclip paths a Runtime would not control either | **Do not build now.** Revisit after OQ-043 |
| 3 Provider adapters | None: `claude_local` and `cursor` work natively. The Codex adapter is blocked by OQ-010, not by missing code | Paperclip's own adapters | **Do not build** |
| 4 Workspace + Git manager | None: Paperclip owns worktrees (C-001, ADR006-6 PASS) | Paperclip | **Do not build** (the roadmap's own condition) |
| 5 Result reporter + outbox | None recorded (no lost results) | Agents report through the skill's reporting script | **Do not build** |
| 6 Recovery sweep | G-1, reviewer not woken: OQ-035 | `runtime/tools/review-wake-watchdog.ts` (IMPLEMENTED, a gap filler) | **Do not build** a sweep; keep the watchdog; report upstream (OQ-035) |
| 7 Wire as `process` agent, re-run Phase 1 Tasks | — | — | **Not applicable** without components 2–6 |

- **OQ-013 (language) and OQ-014 (state store)** stay open. They need resolving only if a component is approved later. **Flagged, not resolved.**
- **Phase 3 disposition: not built.** This needs Board confirmation (D-11). G-14, the critical Stage 1 gap, is closed by the deployment mode (OQ-043), not by a Runtime.

## 6. Phase 4 plan (hardening)

| Area | Risk / failure model | Options | Recommended controls | Tests and observability | Acceptance |
|---|---|---|---|---|---|
| P4-T01 Resource limits (OQ-015) | Many concurrent runs on one machine: memory, quota, cost. `maxConcurrentRuns` is 20 per agent; WIP 1 is enforced only on `release` | <ul><li>`maxConcurrentRuns: 1` per agent (OQ-041: wakes queue, not drop);</li><li>a Windows Job Object (needs a Runtime, not built);</li><li>provider budgets</li></ul> | Set `maxConcurrentRuns: 1` for code-writing agents in `config/paperclip/agents.json`; apply live only with authorization; keep Paperclip budgets | Offline build check; a live read of agent runtime configs; daily triage | The config change is merged; the live apply is authorized and verified, or deferred |
| P4-T02 Stronger isolation (OQ-027, OQ-043, G-13, G-14) | X-1: an agent shell acts as the Board. Same-user file access (R4.2). Cursor agents unguarded (X-3) | <ul><li>Authenticated mode (OQ-043; the A5 plan exists);</li><li>a dedicated Windows user with NTFS ACLs (OQ-027, feasibility UNVERIFIED);</li><li>moving the Cursor roles to Claude profiles</li></ul> | <ol><li>Execute the authenticated-mode migration: scripts gain board-token support (repository work), then a live migration with its own authorization (D-AUTH series);</li><li>a feasibility spike for a dedicated agent user in a sandbox;</li><li>the D-05 decision on Cursor</li></ol> | Offline tests for board-token support in `pc.py`, `post-import.py` and `sync-instructions.py`, and in the watchdog (TypeScript: TO CONFIRM how to test); the V3 probe repeated after the migration must fail | The V3 probe refused; agents keep working; rollback documented |
| P4-T03 Merge-approval linkage (OQ-005, OQ-016, G-4) | A merge without a Paperclip approval, or in the wrong order (seen twice: GAM-20, GAM-44); the owner bypasses protection (B5) | <ul><li>A read-only audit that joins PRs and issues (as the Phase 1 ledger did);</li><li>a pre-merge check run by the Board;</li><li>GitHub automation (OQ-016, needs an ADR)</li></ul> | A read-only `pc.py merge-audit` that lists merged PRs whose issue lacks an approved approval stage or was approved after the merge. Run weekly. No automation | Offline unittest with fake Paperclip and GitHub data; one read-only live run | Flags GAM-20 and GAM-44 on the historical data; no false positives on the 38 full-chain Tasks |
| P4-T04 Multi-provider comparisons (ADR-015, proposed) | Provider choice without evidence; the reviewer on the same provider as the author | Evidence protocol: the same Task class on two providers, measured on findings, rework and cost | A written comparison protocol and a results table in provider-allocation.md. Live runs only with authorization. Codex excluded until OQ-010 (D-09) | Recorded runs; no code | Protocol approved; at least one comparison recorded, or deferred by the Board |

## 7. Dependency and sequencing map

- **Critical path:** D-01…D-03 → P1-T01, P1-T02, P1-T06 → P1-T07 → **Phase 1 gate** → P2-T01, P2-T02 (P2-T03 if D-10) → D-11 (Phase 3 disposition) → P4-T03 (repository-only) → P4-T01, P4-T02 live parts (each BLOCKED until authorized) → final audit.
- **Parallel:** P1-T03, P1-T04 and P1-T05 alongside everything else. P2-T01 and P2-T02 are independent of each other. P4-T03 can start right after the Phase 1 gate.
- **Serialized:** P2-T01 after P1-T06 (it validates the corrected registry). The P4-T02 migration after its script work.
- **External dependencies:** Board decisions; Paperclip version stability (the B6 re-check list applies to any upgrade); Codex quota (OQ-010).

## 8. Test strategy

**Existing commands** (discovered in the repository; stdlib `unittest`, no Paperclip needed):
- `python -I -W error .claude/skills/paperclip/scripts/test_pc.py` (it also runs the `review_pack` and `review_github` tests)
- `python -I -W error .claude/skills/paperclip/scripts/test_review_pack.py`
- `python -I -W error .claude/skills/paperclip/scripts/test_review_github.py`
- `python -I -W error .claude/skills/paperclip/scripts/test_review_relay.py`
- `python -I -W error scripts/setup/test_build_package.py`
- `python -I -W error scripts/setup/test_post_import.py`
- **Dry runs:**
  - `python -I scripts/maintenance/move-files.py <map> --dry-run`
  - `python -I scripts/setup/sync-instructions.py --company Soucean --dry-run` (read-only Paperclip)

**Not available:**
- lint, format, type check: no tooling is configured in the repository. TO CONFIRM whether the Board wants any;
- CI;
- a Markdown link checker;
- tests for `runtime/tools/review-wake-watchdog.ts`.

**Rules:**
- **New tests:** every new tool gets an offline unittest with fixtures, and must fail on the code before the change.
- **PASS:** run and green.
- **FAIL:** run and red.
- **BLOCKED:** needs live services, credentials or a Board action. It is listed, never reported as passed.
- **Needs live access or Board action:** P1-T02, P1-T08/T09/T10 live applies, P2-T03's live run, P4-T01/T02 live parts, P4-T04 runs.

## 9. Security and operations

- **Trust boundaries:**
  - the Board machine is a single Windows user;
  - Paperclip runs in `local_trusted` (X-1);
  - agents run as the same user;
  - GitHub enforces branch protection, except for the owner account (X-2).
- **Credentials:**
  - the shared `GH_TOKEN` (ADR-022) and the packager token (Credential Manager);
  - no new credential in this plan;
  - nothing in this plan prints secrets;
  - the redaction gap (`env` secrets in run logs) is mitigated for Claude agents only.
- **New tools (P2, P4-T03):** read-only and idempotent; no retries that write; no concurrency concerns (single process).
- **Recovery, backup and rollback:**
  - any live configuration change follows the existing pattern: database backup first, read back afterwards, record in the PR;
  - each repository change is a revertible PR.
- **Logging and retention:** run-log retention is to be stated (P1-T05); the audit tools write nothing.
- **Migrations:** only P4-T02 (authenticated mode). It has its own plan and decision series (A5, D-AUTH-10 to D-AUTH-15; implementation authorization pending).

## 10. Decision and blocker register

**Board decisions of 2026-11-21** (Board Operator, in chat), after Stage A:
- **Phase 0:** skip Codex for now; there is no account (D-09: drop for now).
- **Phase 1:** do the remaining work.
- **Phase 2:** build.
- **Phase 3:** confirmed, not built (D-11).
- **Phase 4:** build.
- **Answers to the follow-up questions:**
  - soucean-game is `active` (D-03);
  - Cursor agents are an accepted risk for now (D-05);
  - isolated auth-migration runs are authorized (WS-1, WS-2, WS-5);
  - claim-URL log lines are deleted after the claim (WS-4).

**Pending, each still needing an explicit answer:**
- D-04, D-06, D-07, D-08: each is a live configuration change or a GitHub setting;
- every live action listed as BLOCKED.

"Do the remaining work" covers the repository-local Phase 1 tasks and the recommended wording for D-01 and D-02.


The recommendations below are not approvals.

| ID | Question | Evidence | Options | Recommendation | Blocks |
|---|---|---|---|---|---|
| D-01 | Is the Phase 1 "7 Agent Instances" target updated to the current roster (8 live, plus `code-reviewer` proposed)? | agents.json; live read | Update the wording / keep 7 | Update to the roster from agents.json | P1-T01 |
| D-02 | Does the package-import path replace the hire-request and trial-Task steps of agent-onboarding, or must the Test Environment and trial steps be run per agent? | company-bootstrap.md; no trial record | Accept the import path and record it / run the checks live (authorization) | Accept the import path; run Test Environment per agent once, read-only, when next authorized | P1-T02 |
| D-03 | Is `soucean-game` initialization finished (status `active`)? | Seeded (GAM-20), milestones M1 done, M2 under way | Set `active` / keep `initializing` | The Board confirms; then P1-T06 sets it | P1-T06 |
| D-04 | Narrow `Bash(cat *)` and `npm run *` in the Claude profiles (R4.2, R4.3)? | Matrix R4.2, R4.3 | Narrow / accept the risk | Narrow `cat` to the workspace if the agents' work allows; decide `npm run` per project | P1-T08 |
| D-05 | Cursor agents without allow lists: accept, move the roles to Claude, or find a Cursor-side control? | X-3; a Cursor deny list is UNVERIFIED | Accept / move / investigate | Record as an accepted risk now; investigate a Cursor control in P4-T02 | P4-T02 |
| D-06 | Do agents keep `mcp__Paperclip_projects` task creation (G-9, R2.8)? | G-9 | Remove / keep with triage | Remove for roles that do not plan work; keep for `project-manager` with triage | P1-T09 |
| D-07 | Protect `main` of `datpham02/company-os`? | X-4 | Protect / accept | Protect (PR required); the owner still merges | P1-T10 |
| D-08 | Keep `canCreateAgents` and `canCreateSkills` as granted? | R3.1, R5.3 | Keep / reduce | Verify whether `hire_agent` approval applies, then reduce if it does not | — |
| D-09 | Is Codex still a planned provider? | OQ-010: `exec` never worked | Pursue / drop for now | Drop for now; revisit with quota | 0.2, 0.7, P4-T04 |
| D-10 | Build the agent configuration drift check (P2-T03)? | Drift seen 2026-11-21 | Build / skip | Build | P2-T03 |
| D-11 | Phase 3: confirm "not built" for every component? | §5 | Confirm / approve a component | Confirm | Phase 3 gate |

## 11. Phase gates

| Gate | Mandatory criteria (from phases.md) | Evidence required | Transition |
|---|---|---|---|
| **Phase 1** | Items 1–5 done | <ul><li>Roster, onboarding decision, token and protection, registry conformance, the Task ledger (≥5 qualifying Tasks: 38 recorded), and the MUST matrix accepted by the Board;</li><li>open GAP and PARTIAL items each with a decision or a Phase 2/4 task.</li></ul> Claude self-review of the docs; `git diff --check` | Board approval to start Phase 2 |
| **Phase 2** | Only tools Phase 1 shows are needed | P2-T01, P2-T02 (P2-T03 if approved) merged; offline tests pass and fail on the old code; each runs read-only on the real files | Board decision D-11 |
| **Phase 3** | Built only for verified gaps | D-11 recorded. If "not built": the disposition is documented here and in the gap analysis | Board approval to start Phase 4 |
| **Phase 4** | Resource limits, isolation, merge-approval linkage, provider comparisons | <ul><li>P4-T03 merged and run read-only;</li><li>P4-T01 and P4-T02 repository parts merged; their live parts done with authorization, or recorded as BLOCKED or DEFERRED;</li><li>P4-T04 protocol.</li></ul> Final Phase 0–4 cross-phase audit | End of this mission (no rollout) |

## 12. Effort and uncertainty

- **Phase 1 remaining:** S overall, mostly documentation. Uncertainty is in the Board decisions, not the work.
- **Phase 2:** S–M. The registry validator needs a stdlib YAML reader; no third-party package is approved. TO CONFIRM.
- **Phase 3:** none if D-11 confirms.
- **Phase 4:** P4-T03 S; P4-T01 S (the live apply is separate); P4-T02 L (the authenticated migration has its own plan); P4-T04 M (mostly runs, needs authorization).
- **No dates are given.** The pace depends on Board decisions and authorizations.

## 13. Stage B progress (2026-11-21)

Repository work only, on branch `docs/roadmap-stage-a`. **No live Paperclip, GitHub, credential or ACL change was made.** Read-only live runs are marked "live read".

| Task | State | Evidence |
|---|---|---|
| Phase 0 | Skipped by the Board (Codex deferred, no account; OQ-010) | open-questions OQ-010 |
| P1-T01, T03–T06 (register and document drift) | Done | `phases.md`, `open-questions.md` (OQ-005, 008, 010, 017, 024, 028), `dependencies/registry.yaml`, `security-operations.md` §2 (ADR-022), `agent-onboarding.md` (package import), `company-bootstrap.md`, `knowledge/projects/registry.yaml` |
| P1 item 4 (Task ledger) and item 5 (MUST matrix) | Done, draft for the Board (P1-T07) | `stage1-gap-analysis.md` |
| P1-T02, T08–T10 (D-04, D-06, D-07, Test Environment runs) | **Pending** Board decisions or live authorization | §10 |
| P2-T01 registry validator | Done; live read: 0 findings | `scripts/maintenance/validate-registries.py`, `yaml_subset.py`, `test_registry_tools.py` (10 tests) |
| P2-T02 dependency check | Done; live read found real drift: cursor-cli 2026.11.05 installed, 2026.10.22 recorded. The registry is **not** updated: recording an upgrade needs Board approval (R3.1) | `scripts/maintenance/check-dependencies.py` |
| P2-T03 agent drift check (D-10) | Done; live read: 0 drifts before P4-T01, 2 after (expected, see P4-T01) | `scripts/setup/check-agent-drift.py`, `test_check_agent_drift.py` (5 tests) |
| Phase 3 | Not built (D-11 confirmed) | §5 |
| P4-T01 resource limits | Repository part done: `maxConcurrentRuns: 1` and heartbeat off for `gameplay-programmer` and `game-designer` in `agents.json`. **Live apply pending** authorization | `check-agent-drift.py` reports the 2 differences |
| P4-T02 isolation | Repository part done: Board-token support in every Board script, participant migration tool, sandbox tool. WS-1 restore **passed** in isolation on 2026-11-21 (method acceptance pending); WS-2, WS-5 and the live migration **not done** | [auth-migration-phase-b.md](../architecture/auth-migration-phase-b.md) |
| P4-T03 merge audit | Done as `scripts/maintenance/merge-audit.py` (not a `pc.py` subcommand: it needs `gh` and reads several companies). Live read: 5 findings, the expected GAM-20 and GAM-44 plus GAM-22 (no approval stage) and two unlinked lamplight PRs (#11, #19); no false positive on the full-chain Tasks | `test_merge_audit.py` (4 tests) |
| P4-T04 provider comparison | Protocol written; no run (needs authorization) | `provider-allocation.md` §6 |

**Live actions awaiting the Board:**
1. P4-T01: apply `maxConcurrentRuns: 1` to the two agents (`post-import.py` path or a targeted PATCH, after a database backup).
2. Decisions D-04, D-06, D-07, D-08 and the P1-T02 Test Environment runs.
3. The cursor-cli version in `dependencies/registry.yaml` (R3.1).
4. Authentication: accept the WS-1 cold-copy restore method (E8); the isolated runs WS-2 and WS-5 (authorized; need the live instance stopped and the Board Operator in a browser); the WS-3 run authorization; the WS-6 ACL option; Phase D.

# Review Package R1: reviewer profile validation

- **Date:** 2026-11-21. R1 as a whole ran **04:00–04:12 UTC**:
  - Phases A and B 04:00–04:03 (the live B3 check 04:02:36–04:02:45);
  - Phase C 04:05–04:08;
  - Phase D 04:08–04:12.
- **Code:** `main` at `50ac09b` (PR #50 merged): `review_relay.check_reviewer_config`, run by `review-start`.
- **Status:**
  - Phase A (inventory) done: [review-package-r1-reviewer-inventory.md](review-package-r1-reviewer-inventory.md);
  - Phase B (validation) done;
  - **Phase C (apply) done 2026-11-21, 04:05–04:08 UTC, after the Board Operator's approval ("Duyệt Phase C")**, see §4;
  - **Phase D (live verification) done 2026-11-21, 04:08–04:12 UTC, after the Board Operator's approval ("duyệt DF", read as Phase D)**, see §5.

## 1. Phase B1–B2: requirement by requirement

Each reviewer was checked against the 18 R1 requirements, individually, so that every failure is listed (the validator itself stops at the first).

| Requirement | REV | RPR | OPT |
|---|---|---|---|
| Adapter `claude_local` | pass | pass | pass |
| No environment overrides | pass | pass | pass |
| `dangerouslySkipPermissions` off | pass | pass | pass |
| `--restricted` | pass | pass | pass |
| `--tools` exactly `Read,Grep,Glob` | pass | pass | pass |
| `--disallowedTools` contains `mcp__*` | **fail** | **fail** | **fail** |
| `--permission-mode dontAsk` | pass | pass | pass |
| Exactly one `--add-dir`, the staging `current` | pass | pass | pass |
| No `--allowedTools` | pass | pass | pass |
| No `--dangerously-skip-permissions` | pass | pass | pass |
| No `--mcp-config` | pass | pass | pass |
| No `--permission-prompt-tool` | pass | pass | pass |
| Settings allow exactly Read, Grep, Glob | pass | pass | pass |
| Settings deny contains `mcp__*` | **fail** | **fail** | **fail** |
| Settings deny contains Edit, Write, NotebookEdit, Bash, PowerShell, WebFetch, WebSearch | pass | pass | pass |
| `defaultMode` `dontAsk` | pass | pass | pass |
| No `ask` | pass | pass | pass |
| No `additionalDirectories` | pass | pass | pass |
| **Total** | **16/18** | **16/18** | **16/18** |
| `check_reviewer_config` | refused: "must contain --disallowedTools exactly once" | same | same |

**Conclusion:** all three reviewers need the same two changes, and nothing else.

## 2. Phase B3: refusal before side effects

**Live, OPT, 04:02:36–04:02:45 UTC.** The steps:
1. Staged `OPT-3` (package reused, soucean-game PR #27, read-only).
2. Ran `pc.py --company OPT review-start OPT-3` with the current OPT reviewer profile.
3. Abandoned the staging afterwards.

Paperclip calls were GET only.

| Check | Before | After |
|---|---|---|
| Result | — | `error: the reviewer's extraArgs must contain --disallowedTools exactly once, with a value` |
| OPT issues | 6 | 6 |
| OPT runs (newest) | 11 (03:32:01Z) | 11 (03:32:01Z) |
| `OPT-3` status | `in_review` | `in_review` |
| Staging lock | — | `reviewIssueId: null`, `runId: null`, no `reviewStart` |
| `staging.op` | — | released |
| Audit log | — | `refuse` (`review-start: …`), then `abandon` |
| Soucean newest run | 2026-11-06T06:35:13Z | unchanged |

**The other refusal cases are covered offline** by `test_review_relay.py` `ReviewerConfig` (10 tests). Each asserts that no sub-issue is created and no wake is sent. The cases:
- missing settings `mcp__*` deny;
- Bash, or a Paperclip tool, in `allow`;
- missing `--restricted`, missing or partial `--disallowedTools`;
- `--dangerously-skip-permissions`, `--allowedTools`, `--mcp-config`, `--permission-prompt-tool`;
- wrong or extra `--add-dir`;
- any `env`;
- another adapter;
- unreadable settings or agent.

They were not repeated live in Phase B: that needs separate test profiles (R1 Phase D2).

## 3. Phase C proposal (needs approval)

**For each of REV, RPR and OPT**, only the two missing items:
1. Append to `extraArgs`: `"--disallowedTools", "mcp__*"` (via `PATCH /api/agents/<id>`, `adapterConfig.extraArgs`, keeping every other element and its order).
2. Add `"mcp__*"` to `permissions.deny` in that reviewer's settings file. It is a local file in the private test folder, not Paperclip data.

**Not changed:**
- the author agents and their permissions;
- Soucean;
- agent status (all stay paused; nothing is resumed or woken);
- `canCreateSkills`.

**Afterwards:**
- read back `GET /api/agents/<id>` and the settings file;
- run `check_reviewer_config` (expected PASS);
- run `probe_reviewer_tools.py --settings <file>` (expected PASS).

**Rollback:** Paperclip's agent configuration revisions, or a `PATCH` back to the `extraArgs` recorded in the inventory; restore the settings `deny` list from the inventory.

**Phase D after C:**
- D1: one positive live review, which costs one reviewer run and needs a staged review and a parent issue in `in_review`;
- D2: negative test profiles, preferably on a separate test agent so the three reviewers stay valid;
- D3: side-effect checks as in §2.

## 4. Phase C: applied

**Before any change:**
- database backup `paperclip-20261121-110545.sql.gz`, `gzip -t` OK (not proof of a restore);
- a pre-flight re-read of the three agents had to match the inventory exactly (same `extraArgs`, `paused`, no `--disallowedTools`), or nothing would change.

**Changes**, nothing else:

| Reviewer | `extraArgs` | New config revision | Settings file |
|---|---|---|---|
| REV `5312c2d4` | 15 → 17: appended `--disallowedTools mcp__*` | `88d0032f-6b4d-47a2-97de-79c1f24b2cff` | `deny` + `mcp__*`; backup `settings-C1.json.bak-r1` |
| RPR `f098754d` | 15 → 17: same | `6e31460e-6f98-4eb1-a6ab-5750bde54e39` | same |
| OPT `28a57b09` | 15 → 17: same | `e9c10316-0839-451b-9f7a-e019669054e3` | same |

The change was a `PATCH /api/agents/<id>` with only `adapterConfig.extraArgs` (Paperclip merges `adapterConfig` shallowly).

**Read-back and checks:**
- **Agent records:** for each agent, every other `adapterConfig` key and every other agent field was unchanged (timestamps aside); status still `paused`.
- **Config revisions:** each new revision's `beforeConfig`/`afterConfig` differ only in `adapterConfig.extraArgs`.
- **Validator:** `check_reviewer_config` **PASS** for all three; the 18-requirement check **18/18** for all three.
- **`probe_reviewer_tools.py --settings <each settings file>`:** **PASS** for all three (full profile, settings deny only, flag only). The model was offered exactly Glob, Grep, Read, and the write tool never reached the throwaway server.
- **Side effects:**
  - no agent resumed or woken;
  - no new run in REV (3 runs, newest 2026-11-20 17:14Z), RPR (5, 02:46Z) or OPT (11, 03:32Z);
  - author agents still paused;
  - Soucean: newest run still 2026-11-06, agents idle.

**Rollback:**
- `POST /api/agents/<id>/config-revisions/<previous revision>/rollback`, or a `PATCH` restoring the 15-element `extraArgs`;
- restore each settings file from its `.bak-r1`.

The pre-change state is kept without secrets in the private `pc-r1/inventory-before.json`, rebuilt from the revisions' `beforeConfig` and the `.bak-r1` files after the first `inventory.json` was overwritten by the post-change inventory run.

## 5. Phase D: live verification (OPT)

**Baseline:**
- OPT 6 issues / 11 runs (newest 03:32:01Z);
- REV 1 / 3; RPR 1 / 5;
- Soucean 30 / 152 (newest 2026-11-06);
- every sandbox agent paused.

`OPT-3` was staged again (package reused, soucean-game PR #27, read-only) and was `in_review` with participant `local-board`.

### D2: invalid profiles refused before any side effect

A separate test agent `code-reviewer-negtest` (`4ac03856…`) was created in OPT and **paused**, never assigned, released or woken. For each case its `extraArgs` (and its own copy of the settings file) were set, then `review-start` was called for `OPT-3` with that agent as reviewer.

| Case | Result | OPT issues / runs, lock sub-issue / run |
|---|---|---|
| Settings without `mcp__*` deny | refused: "settings must deny ['mcp__*']" | 6 / 11, none / none → unchanged |
| `Bash` in allow | refused: "allow exactly Read, Grep and Glob" | unchanged |
| Missing `--restricted` | refused: "lack --restricted" | unchanged |
| Missing `--disallowedTools mcp__*` | refused: "--disallowedTools exactly once" | unchanged |
| `--dangerously-skip-permissions` | refused: "forbidden flags" | unchanged |
| Wrong staging directory | refused: "--add-dir must be the staging folder" | unchanged |

The test agent stayed `paused` throughout.

### D1: positive review with the updated reviewer

The OPT `code-reviewer` was resumed for this review only and paused right after its run.

| Step | Result |
|---|---|
| `review-start OPT-3` | Passed the configuration check; created sub-issue `OPT-7` (one) and run `021f2cdb` (one) |
| Run | `succeeded`; `scopeKind: issue`, `issueId` = `OPT-7`; wake reason `review 373bc218-… OPT-3 7f22f059666b`, `triggeredBy: board`, `actorId: local-board`; about US$0.055 |
| **Tool inventory** | `init.tools` = **exactly `Glob`, `Grep`, `Read`**, although Paperclip's "Paperclip projects" and "Paperclip connections" MCP servers were **connected**: the profile removed every MCP tool on a real Paperclip run. Tool uses: Glob and Read only (10); no permission denial |
| Log | `fetch_verified_log`: whole log read, size and SHA-256 match `logBytes`/`logSha256`; `check_tool_surface` PASS |
| Verdict | `changes_requested`, 2 findings; `reviewId` and `challenge` correct |
| Relay | Recorded `changes_requested` (one comment with receipt) and closed `OPT-7`; a second relay: "already relayed", nothing written |

### D3: side effects

After the review, OPT had 7 issues and 13 runs. The changes:
- **+1 issue:** sub-issue `OPT-7`, expected.
- **+2 runs:**
  - the reviewer run `021f2cdb`;
  - `bd8ff6b9`, Paperclip's `issue_disposition_repair` on `OPT-7`, cancelled with `agent_paused`. This is the known follow-up from the Option B check, held off by pausing the reviewer.
- **No author run.** `OPT-3` went back to the paused placeholder author (`in_progress`, `changes_requested`).
- **No other changes:** REV 1 / 3, RPR 1 / 5 and Soucean 30 / 152 unchanged; all agents paused (Soucean idle). Staging unstaged afterwards. No credential in any report.

## 6. Acceptance status (R1 §7)

| Criterion | Status |
|---|---|
| Inventory for REV, RPR, OPT | Done |
| No secrets in the reports | Done (env key names only, none present; prompts by length) |
| Reviewer profiles updated after approval | **Done** (§4) |
| Paperclip API and settings file match | **Done**: validator PASS, 18/18, probe PASS for all three |
| Positive test | **Done** (§5 D1) |
| Negative tests | **Done**: offline (10 tests) and live (6 cases, §5 D2) |
| No unintended side effects | **Done** (§2, §4, §5 D3): only the intended changes listed below the table |
| Evidence and timestamps | **Done** for A–D |
| Sandbox reviewers retained; Soucean untouched | **Done**: the REV, RPR and OPT reviewers are kept (updated, paused); the OPT test agent `code-reviewer-negtest` is kept (paused); Soucean has no reviewer and nothing in it changed |

**Intended changes made by R1** (everything else was checked unchanged):
- **Phase C (approved):** the three reviewers' `extraArgs` (+ `--disallowedTools mcp__*`), their settings `deny` (+ `mcp__*`), and three new config revisions.
- **Phase D:**
  - test agent `code-reviewer-negtest` (paused);
  - sub-issue `OPT-7`;
  - reviewer run `021f2cdb`;
  - Paperclip's cancelled `issue_disposition_repair` run `bd8ff6b9`;
  - on `OPT-3`: one relay comment and the `changes_requested` decision.

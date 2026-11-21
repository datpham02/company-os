# Review Package R1: reviewer profile validation

- **Date:** 2026-11-21, 04:00–04:03 UTC.
- **Code:** `main` at `50ac09b` (PR #50 merged): `review_relay.check_reviewer_config`, run by `review-start`.
- **Status:**
  - Phase A (inventory) done: [review-package-r1-reviewer-inventory.md](review-package-r1-reviewer-inventory.md);
  - Phase B (validation) done;
  - **Phase C (apply) and Phase D (verification) not started: they need the Board's approval to change Paperclip configuration.**

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

## 4. Acceptance status (R1 §7)

| Criterion | Status |
|---|---|
| Inventory for REV, RPR, OPT | Done |
| No secrets in the reports | Done (env key names only, none present; prompts by length) |
| Reviewer profiles updated after approval | **Pending approval** |
| Paperclip API and settings file match | Pending (after C) |
| Positive test | Pending (D1) |
| Negative tests | Offline done; live pending (D2) |
| No side effects | Done for B3; pending for C and D |
| Evidence and timestamps | Done for A and B |
| Profiles not updated or sandboxes gone | All three exist and are not updated; Soucean has no reviewer |

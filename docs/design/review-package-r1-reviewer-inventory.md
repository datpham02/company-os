# Review Package R1: reviewer profile inventory

- **Date:** 2026-11-21, 04:00–04:03 UTC.
- **Scope:** R1 Phase A, read-only: `GET /api/companies`, `GET /api/companies/<id>/agents`, `GET /api/agents/<id>` and each reviewer's local settings file.
- **Code:** `main` at `50ac09b` (PR #50 merged); `test_pc.py` 311 OK.
- **No Paperclip configuration was changed.** Environment variables are listed by key name only; none exist. The reviewers' system prompts are shown by length only. No token or credential appears here.

## 1. Companies and reviewer agents

| Company | Prefix | Status | Agents | `code-reviewer` |
|---|---|---|---|---|
| Review Relay Test | `REV` | active | 1 | `5312c2d4…`, paused |
| RP5 Review Sandbox | `RPR` | active | 2 | `f098754d…`, paused |
| Option B Review Sandbox | `OPT` | active | 2 | `28a57b09…`, paused |
| Soucean | `SOU` | active | 8 | **none** (not changed in R1) |
| Game Studio Soucean | `GAM` | archived | 8 | none |

## 2. Reviewer configuration

All three reviewers have the same shape, created in Phases 4b, 5 and the Option B check.

| Field | REV | RPR | OPT |
|---|---|---|---|
| Adapter | `claude_local` | `claude_local` | `claude_local` |
| Model | `sonnet` | `sonnet` | `sonnet` |
| Status | paused | paused | paused |
| Heartbeat | off, `maxConcurrentRuns` 1 | same | same |
| `env` | none | none | none |
| `dangerouslySkipPermissions` | false | false | false |
| Agent permissions | `canCreateAgents: false`, `canCreateSkills: true` | same | same |
| `cwd` | private `pc-rp4/reviewer-cwd` | `pc-rp5/reviewer-cwd` | `pc-rp6/reviewer-cwd` |
| `--add-dir` (one) | `pc-rp4/staging-root/current` | `pc-rp5/staging-root/current` | `pc-rp6/staging-root/current` |
| `--settings` | `pc-rp4/settings/settings-C1.json` | `pc-rp5/…` | `pc-rp6/…` |

**`extraArgs` (identical except paths and prompt length):**

```text
--no-session-persistence --restricted --tools Read,Grep,Glob --strict-mcp-config
--permission-mode dontAsk --permission-prompts none --settings <settings-C1.json>
--add-dir <staging-root>/current --append-system-prompt <review-only role, 399 / 557 / 578 chars>
```

**Settings `permissions` (identical in all three):**

```json
{"allow": ["Read", "Grep", "Glob"],
 "deny": ["Edit", "Write", "NotebookEdit", "Bash", "PowerShell", "WebFetch", "WebSearch"],
 "defaultMode": "dontAsk"}
```

No `ask`, no `additionalDirectories`.

## 3. Observations

- **No reviewer has the P0 profile.** `--disallowedTools mcp__*` is missing from `extraArgs`, and `mcp__*` is missing from the settings' `deny` list. Details in [the validation results](review-package-r1-validation-results.md).
- **`canCreateSkills: true`** is Paperclip's default agent permission. The reviewer has no tool to use it (no MCP, no shell, no network), and the R1 validator does not check it. Recorded for R2; not changed.
- **Soucean has no `code-reviewer`.** Nothing to synchronize there; production use is Phase 6.
- The private test folders (`pc-rp4`, `pc-rp5`, `pc-rp6`) and their settings files still exist.

## 4. Backup for Phase C

This inventory and its machine-readable form (kept in the private `pc-r1` folder: `inventory.json`) record every reviewer's `extraArgs` and settings permissions before any change. They contain no secrets. Paperclip also keeps agent configuration revisions, which give a rollback path (`POST /api/agents/<id>/config-revisions/<id>/rollback`, used in D-STEP2-01).

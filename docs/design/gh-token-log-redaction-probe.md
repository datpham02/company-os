# GH_TOKEN log redaction probe (ADR-022 follow-up)

- **Date:** 2026-11-21, after the Board Operator's approval ("oke test đi").
- **Question:** when a code-writing agent's command prints a secret bound as `env.GH_TOKEN` (`secret_ref`), does Paperclip 2026.1023.0 hide the value in the run log?
- **Answer: no.** The value is stored and served in plain text in the run log. Only the adapter-invocation metadata hides it.
- **Where:**
  - sandbox company `OPT` only, with a **fake** secret value; no real token was used;
  - a database backup was taken first (`paperclip-20261121-123927.sql.gz`; not proof of a restore);
  - Soucean was not touched.

## 1. Source reading (`@paperclipai/server/dist`)

- **Run log writes** (`services/heartbeat.js`, `appendIdentityRedactedLog`) redact only:
  - the agent's identity private key (`agent-identity-redaction.js`);
  - the current user's name and home path (`log-redaction.js`).
- **Adapter invocation event:** `onAdapterMeta` replaces every secret-bound `env` key with `***REDACTED***`. Run failure reports also use the secret values (`collectRunFailureSecretValues`).
- **Read-time redaction** (`run-secret-redaction.js`, applied by the run, events and log routes) covers only values registered with `register`. Only the agent secret API registers values (`POST /agents/me/secrets/:key/value`, `routes/secrets.js`). A value resolved into `env` at run start is not registered.

## 2. Live probe

**Setup:**
- Secret `REDACTION_PROBE_FAKE` with the value `FAKEPROBEA188FAA002689160`.
- New agent `redaction-probe`:
  - `claude_local`, `sonnet`, heartbeat off;
  - profile `--restricted --tools Bash --allowedTools "Bash(printenv GH_TOKEN)" --strict-mcp-config --permission-mode dontAsk`;
  - `env.GH_TOKEN` bound to that secret by reference;
  - empty working directory.
- Issue `OPT-9` asked the agent to run `printenv GH_TOKEN` once.

Runs:
- `f60a1d20`: the probe run.
- `ae3b7706` and `2aa14ee6`: Paperclip's follow-up runs for the issue's disposition. They ran no command that prints the value.

| Place (run `f60a1d20`) | Fake value present | Redaction marker |
|---|---|---|
| Run log, API `GET /heartbeat-runs/<id>/log` | **Yes**, 2 times (the `tool_result` of `printenv`) | No |
| Run log file on disk (`local_file` store, `.ndjson`, not compressed) | **Yes**, 2 times | No |
| Run detail, API `GET /heartbeat-runs/<id>` | **Yes**, 2 times (result excerpt) | No |
| Run events, API `GET /heartbeat-runs/<id>/events` | No | Yes: `adapter.invoke` `env.GH_TOKEN` = `***REDACTED***` |
| Issue and comments | No | — |

## 3. Consequences

- **A bound `GH_TOKEN` is as safe as the agent's commands.** Any command that prints it puts the real token in the stored run log and in API responses. Examples: `printenv`, `env`, `set`, a script that echoes its environment, or a tool error that quotes it.
- **Who can read it:** anyone who can read run logs, including through `pc.py log`, plus the log files under the Paperclip instance folder (same-user access, G-14).
- The ADR-022 accepted risk "one leaked token exposes every repository of the account" therefore includes leaks through run logs. That risk is not hypothetical.
- **Mitigations available today (Board decisions; none applied by this probe):**
  - **Keep agent instructions explicit:** never print environment variables or credentials. This is procedural only.
  - **Deny environment-dumping commands** (`printenv`, `env`, `set`, `Get-ChildItem env:`) in the Claude permission profiles. Cursor agents have a general shell, so this does not hold for them.
  - **Rotate the token at once** if any run log shows it. Search logs for the token's fixed prefix `github_pat_` without printing matches.
  - **Paperclip's own route:** an agent fetches a secret through the agent secret API, which registers the value for read-time redaction, instead of receiving it in `env`. This needs a different binding and has not been tried.

## 4. Left in place

- **Agent `redaction-probe`:** `paused`, `env` emptied.
- **Secret `REDACTION_PROBE_FAKE`:** deleted.
- **`OPT-9`:** `cancelled`.
- The three runs and their logs, which contain only the fake value.
- The probe agent's empty working directory, outside the repository.
- REV, RPR and Soucean are unchanged.

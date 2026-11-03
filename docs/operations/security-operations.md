# Security Operations

Operational procedures implementing [../architecture/security-architecture.md](../architecture/security-architecture.md).

## 1. GitHub setup per Game Repository (Board Operator)

1. Repository visibility: private unless deliberately public.
2. Branch protection (or a ruleset) on the Default Branch:
   - require a pull request before merging, with at least 1 approving review;
   - block force pushes;
   - block deletion;
   - optionally require status checks once CI exists.
3. Enable "Automatically delete head branches" if Task Branches should be removed after merge.

## 2. Agent GitHub token

1. Create a **fine-grained personal access token** (GitHub Settings → Developer settings) with:
   - *Repository access:* only the studio's Game Repositories;
   - *Permissions:* Contents read/write, Pull requests read/write, Metadata read. Nothing else.
   - Expiry: ≤ 90 days (`PROPOSED`).
2. Store it in Paperclip as a company secret; bind it as `GH_TOKEN` only to code-writing agents (`gameplay-programmer`, `ui-designer`, `qa`, `game-designer`).
3. Verify that the token can push a Task Branch and is rejected when pushing to the protected Default Branch.
4. Calendar a rotation before expiry. Rotate immediately if a log or transcript may have exposed it.

## 3. Provider credentials

- Keep `~/.claude` and `~/.codex` readable only by your Windows user (the default for folders in your user profile). Do not move them to a shared location.
- Never pass API keys on command lines.
- If using API keys, set provider-side spending limits in the vendor console, in addition to Paperclip budgets.

## 4. Paperclip

- Run in `local_trusted` mode bound to loopback only (OQ-024). Never expose a `local_trusted` instance on a network: it has no login.
- For remote access, switch to `authenticated` + `private` (e.g. over Tailscale), per Paperclip's deployment docs.
- Review the activity log weekly for unexpected agent actions.

## 5. Permission profile changes

Switching an Agent Instance to `bypass` (Claude `dangerouslySkipPermissions`, Codex `dangerouslyBypassApprovalsAndSandbox`) requires a Board approval (`request_board_approval`) that records: the instance, the reason, compensating controls (protected branches, scoped token), and a review date.

## 6. Incident response

| Event | Immediate action |
|---|---|
| Secret appears in a log, comment, or commit | Rotate the secret first; then remove it from the location (rewriting history needs a deliberate human decision); record in a Task |
| Agent pushed to a protected branch / destructive action | Pause the agent (`POST /api/agents/{id}/pause`); revert via PR; review its permission profile and token scope |
| Suspected prompt injection | Pause the agent; preserve the transcript; identify the injected source (issue text, file, web page) |
| Unknown process consuming resources | Identify via `ps -eo pid,pgid,cmd`; stop the run from Paperclip first, then the process group |

## 7. Periodic checks (`PROPOSED`, monthly)

- [ ] Token expiry dates and scopes
- [ ] Branch protection still enabled on every Game Repository
- [ ] No Agent Instance on `bypass` without a current approval
- [ ] Dependency registry versions vs. installed versions
- [ ] Paperclip version vs. pinned version

## Related documents
[../architecture/security-architecture.md](../architecture/security-architecture.md) · [../../company/RULES.md](../../company/RULES.md)

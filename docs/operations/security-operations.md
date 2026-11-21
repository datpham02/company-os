# Security Operations

Operational procedures implementing [../architecture/security-architecture.md](../architecture/security-architecture.md).

## 1. GitHub setup per Game Repository (Board Operator)

1. Repository visibility: private unless deliberately public. (`lamplight-vigil` and `soucean-game` are deliberately public; see their README files.)
2. Branch protection (or a ruleset) on the Default Branch:
   - require a pull request before merging, with at least 1 approving review;
   - block force pushes;
   - block deletion;
   - optionally require status checks once CI exists.
3. Enable "Automatically delete head branches" if Task Branches should be removed after merge.

## 2. Agent GitHub token

The current model is [ADR-022](../decisions/ADR-022-author-pull-request-credential.md) (2026-11-21): **one shared token for every code-writing agent**, on the Board's own account.

1. Create a **fine-grained personal access token** (GitHub Settings → Developer settings) with:
   - *Repository access:* *All repositories* of the Board's account. This is the Board's choice, an **accepted risk** recorded in ADR-022: the token also reaches repositories whose Default Branch is not protected, such as this framework repository. The stricter alternative is "only the studio's project repositories".
   - *Permissions:* Contents read/write, Pull requests read/write, Metadata read. Nothing else: no administration, workflows, secrets or deletion.
   - *Expiry:* at most 90 days.
2. Store it in Paperclip as the company secret `GH_TOKEN` (a new version when rotating; bindings use `latest`). Bind it, by secret reference only, to the code-writing agents: in Soucean `game-designer`, `ui-designer`, `qa-engineer`, `gameplay-programmer`, `web-engineer` (`config/paperclip/agents.json`). Never to read-only agents.
3. Make each agent clone use the token, not the host login: `credential.helper` reset, then `!gh auth git-credential` (ADR-022; `soucean-game` fixed 2026-11-21).
4. **Known limit:** the token acts as the repository owner, so branch protection does **not** stop it. A test on 2026-11-21 confirmed that the owner's login can push to a protected Default Branch (Review Package R5, B5, an accepted risk). "Rejected when pushing to the protected Default Branch" is therefore **not** a valid check for this token. The Board's review of every PR is the gate.
5. Calendar a rotation before expiry. Rotate immediately if a log or transcript may have exposed it: Paperclip does not redact `env` secrets in run logs ([gh-token-log-redaction-probe.md](../design/gh-token-log-redaction-probe.md)).
6. **The Review Package packager token is separate:**
   - read-only; held in Windows Credential Manager (`company-os/review-packager`), never in an agent's environment;
   - its expiry date and a reminder are kept by the Board ([review-package-runbook.md](review-package-runbook.md)).

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
[../architecture/security-architecture.md](../architecture/security-architecture.md) · [../../knowledge/company/policies/rules.md](../../knowledge/company/policies/rules.md)

# ADR-022: Who Opens an Author's Pull Request, and With Which Credential

- **Status:** Accepted
- **Date:** 2026-11-21
- **Deciders:** Board Operator
- **Decides:** R4 of the Review Package roadmap ([post-Phase 5 assessment](../design/review-package-post-phase5-assessment.md) §4.A, §6, §7 item 5).
- **Related:** ADR-009, ADR-014, ADR-015, OQ-017, OQ-042; [security-architecture.md](../architecture/security-architecture.md), [security-operations.md](../operations/security-operations.md) §2

## Context
The Review Package reads an author's work from a GitHub pull request, so every reviewed Task needs a PR from the Task Branch. The Phase 5 sandbox (`review-package-phase5-sandbox.md` §2) showed:

- **No `gh` credential inside the author run.** `gh pr create` failed because no `GH_TOKEN` was bound to the sandbox author.
- **`git push` still worked,** through the host's Git Credential Manager login. That login is the Board's own account and reaches every repository of it, which is broader than an author needs.
- **The Board side opened the PR** (soucean-game#28) from the pushed branch, with no branch operation.

Production code-writing agents already get a fine-grained `GH_TOKEN` through a Paperclip company secret binding (OQ-017, resolved for the first Game Repository; security-operations.md §2).

## Decision
Two cases.

**1. Review Package sandboxes (throwaway companies and repositories): Board-side PR creation** (assessment §4.A option 2).
- The sandbox author MUST NOT be given a `GH_TOKEN` or any other new credential. It only pushes its Task Branch.
- The Board Operator, or Claude acting on the Board's request in chat, opens the PR from that branch with the Board's own `gh` login: `gh pr create --repo <owner>/<repo> --head <task-branch> --base main`. The title marks it as a sandbox PR.
- Opening the PR MUST NOT create, move, rebase or delete a branch. The PR number then goes to `review-pack --github-pr N`.

**2. Production authors: one shared, scoped author credential** (assessment §4.A option 1, the OQ-017 model; refined by the Board on 2026-11-21).
- The Board issues **one fine-grained personal access token**, shared by every code-writing agent, including `web-engineer`, whose done-criterion is "pushed branch and open PR".
  - **Created by the Board.** Claude and agents never create, read, copy or print it.
  - **Repository access:** *All repositories* of the account, or only the companies' repositories; the Board picks.
  - **Permissions:** Contents read/write, Pull requests read/write, Metadata read. Nothing else: no administration, no workflows, no secrets, no deletion.
  - **Expiry:** at most 90 days, with a rotation date in the Board's calendar.
- The Board considered a single token with full permissions and rejected it. Such a token could:
  - turn off branch protection and merge without the Board (ADR-009);
  - delete repositories or change GitHub Actions;
  - expose the whole account through one leaked run log.
- **Bound only to code-writing agents.** Read-only agents MUST NOT get the token: `director` (read-only), `producer`, `project-manager` and `code-reviewer`.
- The token MUST reach the agent only as a Paperclip company secret bound by reference (`env.GH_TOKEN` as `secret_ref`). It MUST NOT appear as an `env` literal, in a file, on a command line, in an issue, a comment or a log.
- **Every repository the token can push to MUST have `main` protected:** PR required, 1 approval, no force-push, no deletion. With *All repositories*, an unprotected repository is one an agent can push to directly; the Board protects it or narrows the token's repository list.
- **Each agent clone MUST use the token, not the host login:** `credential.helper = !gh auth git-credential` (security-architecture.md). The Phase 5 clone pushed through Git Credential Manager instead, so this is checked on every clone (`git config --get-all credential.helper`) before the token is relied on.
- Before an existing production token is relied on for Review Package Tasks, the Board checks it against these limits. Today's Soucean token was not re-checked as part of this decision.
- `main` stays protected on GitHub (PR required, 1 approval, no force-push, no deletion). The token can open a PR but never merge it (ADR-009).
- The runbook is [security-operations.md](../operations/security-operations.md) §2. A leak is handled by its step 4: rotate immediately.

**Git Credential Manager access** (assessment §4.A, §7 item 5): decided by the measures above. Code-writing agents push with the shared token through `gh`, not with the host login.
- This does not remove the host login from the machine. An agent process whose clone still uses Git Credential Manager, or a read-only agent with a shell, can still reach it.
- The gap closes only once every clone is checked. Until then it stays recorded as open.
- G-14 (same-user processes) is the wider form of this gap.

**Not decided here:** G-13 and G-14. This decision does not affect them, and neither is resolved.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| One shared token with full permissions (the Board's first proposal) | Admin scope can turn off branch protection and merge past the Board; delete and workflow scopes allow irreversible damage after a prompt injection; one leak exposes the whole account. It would also break security-architecture.md's MUST |
| Option 2 (Board-side PR) for production too | One extra Board step per Task; production authors already work with a scoped token (OQ-017) |
| Option 1 for sandboxes | Puts a write credential in throwaway companies for no gain; the Board step is cheap at sandbox volume |
| Option 3, a GitHub App that opens PRs on a Paperclip event | Strongest separation, but highest setup cost and outside the current scope; reconsider below |

## Consequences
- Sandbox runs need no new secret. Each sandbox Task costs one Board step, and the sandbox record says that the Board opened the PR.
- Production authors open their own PRs, as Soucean authors already do. The risk is the same as today: a scoped token with write access to the selected repositories, contained by branch protection and the Board's merge.
- **Follow-up (the Board's):**
  - create the shared token within the limits above, and replace the current Soucean `GH_TOKEN` secret with it, or check the current token against the limits;
  - bind it only to the code-writing agents;
  - protect `main` on every repository the token reaches;
  - check each agent clone's credential helper;
  - confirm on a sandbox run, with a fake secret value, that Paperclip redacts `GH_TOKEN` in run logs (`UNVERIFIED`).

## Reconsider when
- Agents start opening PRs in repositories outside a company's own set, or on a host other than this machine.
- The PR volume makes the Board step or token rotation a burden: consider option 3.
- Paperclip offers per-run, short-lived GitHub credentials.
- A token leak or a push outside the Task Branch is observed.

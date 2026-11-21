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

**2. Production authors: a scoped author credential** (assessment §4.A option 1, the existing OQ-017 model).
- Each code-writing agent that must open its own PR, including `web-engineer`, whose done-criterion is "pushed branch and open PR", gets a **fine-grained personal access token**.
  - **Created by the Board.** Claude and agents never create, read, copy or print it.
  - **Repository access:** only the repositories that company works in.
  - **Permissions:** Contents read/write, Pull requests read/write, Metadata read. Nothing else: no administration, no workflows, no secrets, no deletion.
  - **Expiry:** at most 90 days, with a rotation date in the Board's calendar.
- The token MUST reach the agent only as a Paperclip company secret bound by reference (`env.GH_TOKEN` as `secret_ref`). It MUST NOT appear as an `env` literal, in a file, on a command line, in an issue, a comment or a log.
- Before an existing production token is relied on for Review Package Tasks, the Board checks it against these limits. Today's Soucean token was not re-checked as part of this decision.
- `main` stays protected on GitHub (PR required, 1 approval, no force-push, no deletion). The token can open a PR but never merge it (ADR-009).
- The runbook is [security-operations.md](../operations/security-operations.md) §2. A leak is handled by its step 4: rotate immediately.

**Not decided here:**
- **Narrowing the Git Credential Manager access** that agent processes inherit from the host login. It stays an open least-privilege gap (assessment §4.A and §7 item 5) until the Board decides it separately. Until then, a push by an agent without a bound `GH_TOKEN` can reach every repository of the Board's account.
- **G-13 and G-14.** This decision does not affect them, and neither is resolved.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Option 2 (Board-side PR) for production too | One extra Board step per Task; production authors already work with a scoped token (OQ-017) |
| Option 1 for sandboxes | Puts a write credential in throwaway companies for no gain; the Board step is cheap at sandbox volume |
| Option 3, a GitHub App that opens PRs on a Paperclip event | Strongest separation, but highest setup cost and outside the current scope; reconsider below |

## Consequences
- Sandbox runs need no new secret. Each sandbox Task costs one Board step, and the sandbox record says that the Board opened the PR.
- Production authors open their own PRs, as Soucean authors already do. The risk is the same as today: a scoped token with write access to the selected repositories, contained by branch protection and the Board's merge.
- **Follow-up (the Board's):**
  - check the current Soucean token against the limits above;
  - decide on narrowing Git Credential Manager access;
  - confirm on a sandbox run that Paperclip redacts `GH_TOKEN` in run logs (`UNVERIFIED` for the Review Package flow).

## Reconsider when
- Agents start opening PRs in repositories outside a company's own set, or on a host other than this machine.
- The PR volume makes the Board step or token rotation a burden: consider option 3.
- Paperclip offers per-run, short-lived GitHub credentials.
- A token leak or a push outside the Task Branch is observed.

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
  - **Repository access:** *All repositories* of the Board's account (Board's choice, 2026-11-21), so a new project repository needs no token change.
  - **Permissions:** Contents read/write, Pull requests read/write, Metadata read. Nothing else: no administration, no workflows, no secrets, no deletion.
  - **Expiry:** at most 90 days, with a rotation date in the Board's calendar.
- The Board considered a single token with full permissions and rejected it. Such a token could:
  - turn off branch protection and merge without the Board (ADR-009);
  - delete repositories or change GitHub Actions;
  - expose the whole account through one leaked run log.
- **Bound only to code-writing agents.** Read-only agents MUST NOT get the token: `director` (read-only), `producer`, `project-manager` and `code-reviewer`.
- The token MUST reach the agent only as a Paperclip company secret bound by reference (`env.GH_TOKEN` as `secret_ref`). It MUST NOT appear as an `env` literal, in a file, on a command line, in an issue, a comment or a log.
- **Each agent clone MUST use the token, not the host login:** `credential.helper = !gh auth git-credential` (security-architecture.md). The Phase 5 clone pushed through Git Credential Manager instead, so this is checked on every clone (`git config --get-all credential.helper`) before the token is relied on.
- Before an existing production token is relied on for Review Package Tasks, the Board checks it against these limits. Today's Soucean token was not re-checked as part of this decision.
- Project repositories keep `main` protected on GitHub: PR required, 1 approval, no force-push, no deletion. The Board protects `main` on each new public project repository when creating it (OQ-018).
- The runbook is [security-operations.md](../operations/security-operations.md) §2. A leak is handled by its step 4: rotate immediately.

**Accepted risk: one GitHub identity** (Board decision, 2026-11-21). The token belongs to the Board's own account. The Board chose this over a separate machine account for agents and over a GitHub organization. Consequences the Board accepts:
- **GitHub cannot tell an agent from the Board.** The token acts as the repository owner, who is an admin.
  - Branch protection on `soucean-game` and `lamplight-vigil` allows admin bypass, and the Board relies on that bypass to merge agent PRs (OQ-017: the PR author is the account itself, so nobody else can approve).
  - So the token can probably also push directly to a protected `main`, or merge a PR without approval. This is `UNVERIFIED`; it is not tested, to avoid writing to a real `main`.
  - **The merge gate of ADR-009 is therefore procedural, not enforced by GitHub, for agent tokens.** It rests on:
    - the agents' instructions and permission profiles, which deny pushing to `main` (security-architecture.md);
    - the Board reviewing every PR.
  - Cursor agents (`gameplay-programmer`, `web-engineer`) have a shell, so for them the permission profile is not a hard guard.
- **With *All repositories*, the token can also read and write the Board's other repositories,** where nothing protects `main`:
  - this repository (`company-os`), which holds the agents' rules and the review pipeline;
  - the other public personal repositories;
  - every private repository. GitHub Free cannot protect branches of private repositories.
- **One leaked token exposes every repository of the account.** A probe on 2026-11-21 showed that Paperclip does **not** redact an `env` secret in run logs: a command that prints `GH_TOKEN` stores it in plain text in the run log and serves it through the API ([gh-token-log-redaction-probe.md](../design/gh-token-log-redaction-probe.md)). Only the adapter-invocation metadata hides it.
- Mitigations kept:
  - no administration, workflow or delete permission, so the token cannot change protection, settings or Actions, or delete a repository;
  - expiry at most 90 days;
  - bound only to code-writing agents, and only by secret reference;
  - each clone uses `gh` with the token;
  - the Board reviews every PR;
  - Paperclip run logs keep a record of every agent command.

**Git Credential Manager access** (assessment §4.A, §7 item 5): decided by the measures above. Code-writing agents push with the shared token through `gh`, not with the host login.
- This does not remove the host login from the machine. An agent process whose clone still uses Git Credential Manager, or a read-only agent with a shell, can still reach it.
- **Checked 2026-11-21:**
  - `lamplight-vigil` already resets the helper list and uses `gh`.
  - `soucean-game` asked Git Credential Manager first. That explains the Phase 5 push; it was fixed on the Board's approval by resetting the list, which covers its worktrees.
  - A probe with a fake `GH_TOKEN` value confirmed that git now takes the environment token.
- Every new project clone gets the same configuration, and the check is repeated for it.
- Without a `GH_TOKEN` in its environment, `gh` falls back to the Board's own `gh` login. Every code-writing agent therefore MUST have the token bound.
- G-14 (same-user processes) is the wider form of this gap.

**Not decided here:** G-13 and G-14. This decision does not affect them, and neither is resolved.

## Alternatives considered
| Alternative | Why not chosen |
|---|---|
| One shared token with full permissions (the Board's first proposal) | Admin scope can turn off branch protection and merge past the Board; delete and workflow scopes allow irreversible damage after a prompt injection; one leak exposes the whole account. It would also break security-architecture.md's MUST |
| A separate machine account for agents, invited with Write (not admin) to project repositories | GitHub would enforce the merge gate (no admin bypass) and limit the token to invited repositories. The Board kept one account to avoid managing a second identity; see the accepted risk |
| A GitHub organization for company repositories, token scoped to the organization | Keeps personal repositories out of reach without editing the token per project. Not chosen for now (repository transfers, token re-creation); it does not by itself remove the admin bypass |
| *Only select repositories* | A token edit for every new project repository; the Board chose *All repositories* |
| Option 2 (Board-side PR) for production too | One extra Board step per Task; production authors already work with a scoped token (OQ-017) |
| Option 1 for sandboxes | Puts a write credential in throwaway companies for no gain; the Board step is cheap at sandbox volume |
| Option 3, a GitHub App that opens PRs on a Paperclip event | Strongest separation, but highest setup cost and outside the current scope; reconsider below |

## Consequences
- Sandbox runs need no new secret. Each sandbox Task costs one Board step, and the sandbox record says that the Board opened the PR.
- Production authors open their own PRs, as Soucean authors already do. The token reaches every repository of the Board's account and acts as its owner. The merge gate for agent tokens is procedural (see the accepted risk).
- **Follow-up (the Board's):**
  - put the new token in the Soucean `GH_TOKEN` secret as a new version (the bindings already use `latest`), then revoke the old token;
  - protect `main` on each new public project repository when creating it;
  - repeat the credential-helper check for each new project clone;
  - decide the mitigations listed in gh-token-log-redaction-probe.md §3: deny environment-dumping commands in the Claude profiles, add an explicit instruction for every agent, rotate the token on any log exposure. The log redaction probe was done on 2026-11-21: **not redacted**.

## Reconsider when
- An agent pushes to `main`, merges a PR, or writes to a repository outside its Task: switch to a separate machine account or an organization at once.
- A test on a throwaway repository confirms that the owner's fine-grained token bypasses branch protection. That confirms the accepted risk above, and the Board decides again.
- Agents start opening PRs in repositories outside a company's own set, or on a host other than this machine.
- The PR volume makes the Board step or token rotation a burden: consider option 3.
- Paperclip offers per-run, short-lived GitHub credentials.
- A token leak or a push outside the Task Branch is observed.

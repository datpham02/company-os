# Contributing to Game Studio

This guide applies to humans and AI agents. AI agents MUST also follow [AGENTS.md](AGENTS.md).

## 1. Before you change anything

1. Read [docs/README.md](docs/README.md) and the documents relevant to your change.
2. Check [docs/decisions/README.md](docs/decisions/README.md) for ADRs that constrain your change.
3. Check [docs/architecture/open-questions.md](docs/architecture/open-questions.md) for unresolved questions in the same area.

## 2. Kinds of change

| Change | Requirement |
|---|---|
| Typo, broken link, clarification with no meaning change | Direct edit. |
| New or changed component contract, workflow, or rule | Update the document. Update every document that links to the changed section. |
| Contradicts or replaces an `Accepted` ADR | Write a new ADR with status `Proposed` that names the ADR it would supersede. Do not edit the old ADR's decision. The Board Operator accepts or rejects it. |
| New external tool | Follow [workflows/add-external-dependency.md](workflows/add-external-dependency.md). |
| New agent role | Follow [workflows/agent-onboarding.md](workflows/agent-onboarding.md). |
| New AI execution provider | Follow [workflows/add-execution-provider.md](workflows/add-execution-provider.md). |
| Runtime code | Not accepted until the roadmap's Phase 0 investigation closes ([docs/guides/implementation-roadmap.md](docs/guides/implementation-roadmap.md)). |

## 3. Documentation rules

- Use the normative terms and status labels in [docs/conventions.md](docs/conventions.md).
- Use the terms in [docs/glossary.md](docs/glossary.md). Do not introduce synonyms.
- One topic, one owning document. Link instead of duplicating.
- Every claim about an external system needs a source (URL or commit) or the label `UNVERIFIED`.
- Use relative Markdown links.

## 4. Git

- Branch from `main`; never commit directly to `main` once the repository is under Git.
- Commit messages: imperative mood, one logical change per commit.
- Update [CHANGELOG.md](CHANGELOG.md) under `[Unreleased]`.
- A human reviews and merges. AI agents MUST NOT merge their own changes ([ADR-009](docs/decisions/ADR-009-approval-before-merge.md)).

# Contributing to Company OS

This guide applies to humans and AI agents. AI agents MUST also follow [AGENTS.md](AGENTS.md).

## 1. Before you change anything

1. Read [docs/README.md](docs/README.md) and the documents relevant to your change.
2. Check [docs/decisions/README.md](docs/decisions/README.md) for ADRs that constrain your change.
3. Check [docs/roadmap/open-questions.md](docs/roadmap/open-questions.md) for unresolved questions in the same area.

## 2. Kinds of change

| Change | Requirement |
|---|---|
| Typo, broken link, clarification with no meaning change | Direct edit. |
| New or changed component contract, workflow, or rule | Update the document. Update every document that links to the changed section. |
| Contradicts or replaces an `Accepted` ADR | Write a new ADR with status `Proposed` that names the ADR it would supersede. Do not edit the old ADR's decision. The Board Operator accepts or rejects it. |
| New external tool | Follow [knowledge/company/workflows/add-external-dependency.md](knowledge/company/workflows/add-external-dependency.md). |
| New agent role | Follow [knowledge/company/workflows/agent-onboarding.md](knowledge/company/workflows/agent-onboarding.md). |
| New AI execution provider | Follow [knowledge/company/workflows/add-execution-provider.md](knowledge/company/workflows/add-execution-provider.md). |
| Moving or renaming files | Use `scripts/maintenance/move-files.py` with a mapping file; it rewrites links. Follow the placement rules in [knowledge/departments/README.md](knowledge/departments/README.md#placement-rules). |
| Runtime code | Not accepted until the roadmap's Phase 0 investigation closes ([docs/roadmap/phases.md](docs/roadmap/phases.md)). |

## 3. Documentation rules

- Use the normative terms and status labels in [docs/conventions.md](docs/conventions.md).
- Use the terms in [docs/vision/terminology.md](docs/vision/terminology.md). Do not introduce synonyms.
- One topic, one owning document. Link instead of duplicating.
- Every claim about an external system needs a source (URL or commit) or the label `UNVERIFIED`.
- Use relative Markdown links.

## 4. Git

- Branch from `main`; never commit directly to `main` once the repository is under Git.
- Commit messages: imperative mood, one logical change per commit.
- Update [CHANGELOG.md](CHANGELOG.md) under `[Unreleased]`.
- A human reviews and merges. AI agents MUST NOT merge their own changes ([ADR-009](docs/decisions/ADR-009-approval-before-merge.md)).

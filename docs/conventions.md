# Documentation Conventions

**Owner:** Game Studio maintainers · **Applies to:** every Markdown file in this repository.

## 1. Normative terms

| Term | Meaning |
|---|---|
| **MUST** | Mandatory. Violating it is a defect. |
| **MUST NOT** | Prohibited. |
| **SHOULD** | Recommended. Deviation requires a documented reason. |
| **SHOULD NOT** | Discouraged. Doing it requires a documented reason. |
| **MAY** | Optional. |

Normative terms are written in capitals only when they carry this meaning.

## 2. Status labels

Every requirement, component, command, or capability that is not self-evidently descriptive carries one label, written in backticks.

| Label | Meaning | Who can assign it |
|---|---|---|
| `APPROVED` | Confirmed architectural decision. Traceable to an `Accepted` ADR. | Board Operator (via ADR) |
| `PROPOSED` | Suggested design awaiting approval. MUST NOT be implemented as if approved. | Anyone |
| `PLANNED` | Intended future implementation. Does not exist yet. Commands labelled `PLANNED` MUST NOT be run. | Maintainers |
| `UNVERIFIED` | Claim about behaviour (usually of an external system) that has not been technically validated. Each one has an entry in [architecture/open-questions.md](architecture/open-questions.md). | Anyone |
| `VERIFIED` | Claim about an external system confirmed from its official documentation or by running it, with the source cited. | Anyone, with citation |
| `IMPLEMENTED` | Exists in this repository's code and has been verified. As of v0.1.0 nothing is `IMPLEMENTED`. | Maintainers, after verification |
| `DEPRECATED` | No longer recommended. Names its replacement. | Maintainers |

`VERIFIED` is an addition to the label set required by the original brief. It is needed to distinguish confirmed external facts from `UNVERIFIED` ones.

## 3. Source-of-truth hierarchy

When documents disagree, the higher one wins:

1. `Accepted` ADRs in [decisions/](decisions/).
2. Architecture documents in [architecture/](architecture/).
3. Design documents (component contracts) in [design/](design/).
4. Workflow documents in [../workflows/](../workflows/).
5. Integration documents in [integrations/](integrations/).
6. Operational guides in [operations/](operations/).
7. README files and guides (navigation and summaries only).

Studio content files ([../company/](../company/), [../agents/](../agents/)) are instances of the contracts in `design/`. A conflict between an instance and its contract is resolved in favour of the contract.

**Conflict procedure.** Anyone who finds a conflict MUST NOT silently pick a side. Record it in the *Conflicts* section of [architecture/open-questions.md](architecture/open-questions.md), apply the higher-ranked document in the meantime, and raise it with the Board Operator.

## 4. Document ownership

| Area | Owning document | Rule |
|---|---|---|
| Terminology | [glossary.md](glossary.md) | Other documents use these terms and do not redefine them. |
| Architectural decisions | One ADR per decision | Other documents link to the ADR rather than restating its rationale. |
| A component's contract | Its section in [design/](design/) or [architecture/system-components.md](architecture/system-components.md) | Exactly one owning section per component. |
| A workflow's steps | Its file in [../workflows/](../workflows/) | Design docs describe workflow *structure*, not individual workflows. |
| External interfaces | [integrations/](integrations/) | Other documents link here for CLI flags, endpoints, and environment variables. |
| Unverified assumptions and conflicts | [architecture/open-questions.md](architecture/open-questions.md) | IDs are permanent (`OQ-NNN`, `C-NNN`); closed entries are kept. |

## 5. Cross-references

- Use relative Markdown links: `[runtime architecture](architecture/runtime-architecture.md)`.
- Refer to ADRs as `ADR-NNN` with a link on first mention in each section.
- Refer to open questions as `OQ-NNN` and conflicts as `C-NNN`.
- Refer to agents by **agent ID** in code style: `gameplay-programmer`.
- Refer to workflows by **file name**: [development-cycle](../workflows/development-cycle.md).
- Each document ends with a **Related documents** list.

## 6. Naming

| Thing | Format | Example |
|---|---|---|
| Agent ID | kebab-case, role noun | `gameplay-programmer` |
| Project ID | kebab-case; equal to the GitHub repository name | `node-arena` |
| Dependency ID | kebab-case | `playwright-mcp` |
| Provider ID | snake_case, matching Paperclip adapter type when one exists | `claude_local` |
| ADR file | `ADR-NNN-kebab-title.md` | `ADR-006-git-worktree-for-concurrent-tasks.md` |
| Workflow file | kebab-case verb phrase | `register-existing-repository.md` |

## 7. Writing rules for AI readability

- State **who** acts, **what** triggers it, **inputs**, **outputs**, **owner**, and **failure behaviour**.
- Avoid vague verbs ("handle", "manage", "integrate") unless followed by the concrete actions they mean.
- Prefer tables and numbered steps over prose for contracts and procedures.
- Never present a command as runnable unless it is `VERIFIED` against an installed tool or `IMPLEMENTED` in this repository.

## Related documents

- [glossary.md](glossary.md)
- [README.md](README.md)
- [decisions/ADR-000-template.md](decisions/ADR-000-template.md)

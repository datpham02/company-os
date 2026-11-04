# Knowledge

What the company knows and how it operates: rules, roles, workflows, standards, department charters and project entrypoints. Engineering documentation of Company OS itself lives in [../docs/README.md](../docs/README.md).

Layout decided in [ADR-019](../docs/decisions/ADR-019-knowledge-tree-and-departments.md) (brief v5 §7.8).

## Scopes

| Scope | Folder | Who uses it |
|---|---|---|
| Company | [company/README.md](company/README.md) | Everyone: company rules, shared roles, company workflows, standards, cross-department contracts |
| Department | [departments/README.md](departments/README.md) | People and agents working for that department |
| Project | [projects/README.md](projects/README.md) | Registry and one entrypoint per project; the project's own documents stay in its repository |

## Loading order (brief v5 §7.5)

1. Your role file and your Task.
2. [company/policies/rules.md](company/policies/rules.md) and [company/standards/task-contract.md](company/standards/task-contract.md).
3. Your department's charter (`departments/<dept>/README.md`), then only the domain documents your Task needs.
4. The project entrypoint (`projects/<id>/README.md`), then the project repository's `AGENTS.md`.
5. Anything else only on demand, by targeted search.

## Access

The folders are shaped so that read access can be granted per scope. In v1 nothing enforces it: agents run as the Board's Windows user, and Paperclip agents receive only their role text, not this repository (brief v5 §7.2). Treat another department's folder as off-limits unless your Task names it.

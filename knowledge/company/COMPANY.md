---
name: Soucean
description: An AI-operated company with Game and Web departments, run by one Board Operator.
schema: agentcompanies/v1
---

# Soucean — Company

## Mission
Build and ship original products, games and the website that hosts them, with AI agents under human direction. Run several independent projects at once without losing quality, traceability or control.

## Paperclip company goal (`PROPOSED`)
> Ship original, well-crafted products, one independent project at a time, with every change reviewed and every release approved by the Board.

## Values
1. **Users first.** Product intent beats schedule pressure; conflicts escalate to `director`.
2. **Small, reviewable changes.** Every change lives on its own branch and goes through review.
3. **Humans decide what ships.** Merges, releases and production changes need Board approval.
4. **Write it down.** Decisions, designs and results are recorded where the next agent can find them.
5. **Honesty over optimism.** Report blockers, failures and uncertainty immediately.

## Departments
| Department | Charter | Head |
|---|---|---|
| Game | [../departments/game/README.md](../departments/game/README.md) | `director` |
| Web | [../departments/web/README.md](../departments/web/README.md) | `director` |

Each department adds its own mission, values and scope rules on top of this file.

## Scope
- In scope: products the Board approves in one of the departments; prototypes; tooling the products need.
- Out of scope: project source code inside the framework repository ([ADR-001](../../docs/decisions/ADR-001-single-game-studio-repository.md), [ADR-005](../../docs/decisions/ADR-005-independent-game-repositories.md)). Department scope rules are in each charter.

## Related
[ORGANIZATION.md](ORGANIZATION.md) · [policies/rules.md](policies/rules.md) · [OPERATING_MODEL.md](OPERATING_MODEL.md) · [company-design.md](../../docs/design/company-design.md)

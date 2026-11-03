# Workflow: Add a New AI Execution Provider

- **ID:** `add-execution-provider` · **Owner:** Board Operator · **Board gate:** yes

## Trigger
The studio wants to run agents on another AI coding CLI (e.g. one of Paperclip's other built-in adapters such as `gemini_local` or `opencode_local`, `VERIFIED` as listed in Paperclip docs).

## Required inputs
Provider name; official docs; Paperclip adapter type if one exists.

## Actors
Board Operator; evaluator agent; `qa`.

## Preconditions
Provider added as a Dependency (category `execution-provider`) via [add-external-dependency.md](add-external-dependency.md) up to `approved`.

## Steps
1. **Evaluator** documents in a new `docs/integrations/<provider>-integration.md`, following the structure of [claude-code-integration.md](../docs/integrations/claude-code-integration.md): non-interactive invocation, auth, cwd, prompt delivery, output format, permission/sandbox controls, failure modes. Every flag `VERIFIED` against the installed CLI's help.
2. **Evaluator** maps the studio permission profiles to the provider's controls in [security-architecture.md §4](../docs/architecture/security-architecture.md#4-agent-permissions-provider-level). If `read-only` or `workspace-write` cannot be expressed, the provider is limited to roles whose profile it supports.
3. **Stage 1:** if Paperclip has an adapter for it, register a test Agent Instance with that adapter on a scratch project; run a trivial Task through [development-cycle.md](development-cycle.md).
4. **Stage 2 (`PLANNED`):** implement a `ProviderAdapter` ([runtime-architecture.md §5](../docs/architecture/runtime-architecture.md#5-agent-launcher-and-provider-abstraction)) with tests for invocation building, output parsing, and exit classification.
5. **`qa`** verifies the test Task's outcome and that rules (no Default Branch push, etc.) held.
6. **Board Operator** approves the provider for production use; updates [../company/ORGANIZATION.md](../company/ORGANIZATION.md) if any role's default changes.

## Expected outputs
Integration document; permission mapping; tested Agent Instance; registry `integrated`.

## Approval requirements
Dependency approval; final production approval.

## Failure cases
| Failure | Response |
|---|---|
| No headless mode | Reject; providers must run non-interactively (ADR-004) |
| No way to confine writes | Allow only with Board-approved `bypass` profile restrictions, or reject |

## Related
[../docs/decisions/ADR-008-provider-abstraction.md](../docs/decisions/ADR-008-provider-abstraction.md)

# Workflow: Request Approval

- **ID:** `approval-request` · **Owner:** requesting agent · **Board gate:** this is the gate

## Trigger
An agent needs a decision reserved to the Board ([../company/RULES.md](../company/RULES.md) R3) or a confirmation from a manager.

## Required inputs
What is requested; why; options considered; recommendation; impact/risks; linked Tasks.

## Actors
Requesting agent; approver (Board Operator, or a manager agent for confirmations).

## Preconditions
The request is within the requester's role to propose ([../docs/design/company-design.md §3](../docs/design/company-design.md#3-decision-authority)).

## Steps
1. **Choose the mechanism** (all `VERIFIED` Paperclip features):

   | Decision | Mechanism |
   |---|---|
   | New project, dependency install/upgrade, release, permission profile change | Approval `type: request_board_approval` |
   | New Agent Instance | `POST /api/companies/{companyId}/agent-hires` (creates `hire_agent` approval) |
   | Budget increase | `budget_override_required` approval |
   | Studio strategy (root agent) | `approve_ceo_strategy` |
   | Merge of a Task's code | Task execution policy `approval` stage (see workflow 8) |
   | Plan acceptance inside a Task | `request_confirmation` interaction |

2. **Write the payload**: summary (≤ 5 lines), options with trade-offs, recommendation, links. No secrets.
3. **Submit** and comment on the related Task with a link; set the Task `blocked` if work cannot continue.
4. **Approver** decides: approve, reject, or request revision, with a decision note.
5. **Requester** is woken by the approval-resolution heartbeat (`PAPERCLIP_APPROVAL_ID`, `PAPERCLIP_APPROVAL_STATUS`; `VERIFIED`). Approved → continue. Revision requested → revise and resubmit (`/resubmit`). Rejected → comment and stop the dependent work.

## Expected outputs
A recorded decision with a note, linked to the Task.

## Approval requirements
This workflow is the approval.

## Failure cases
| Failure | Response |
|---|---|
| No decision for 72h (`PROPOSED`) | `producer` includes it in the weekly report as blocking |
| Approval type not available in the installed Paperclip | Use `request_board_approval`; record the gap in OQ-008 |

## Related
[../docs/integrations/paperclip-integration.md §7](../docs/integrations/paperclip-integration.md#7-approval-synchronization) · [../docs/architecture/security-architecture.md §8](../docs/architecture/security-architecture.md#8-approval-boundaries)

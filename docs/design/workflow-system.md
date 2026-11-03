# Workflow System

**Contract owner for:** the structure every workflow follows and how workflows execute through Paperclip. Individual workflows live in [../../workflows/](../../workflows/).

## 1. Execution model

Game Studio has **no workflow engine** in v1 (C-004). A workflow is a Markdown definition. It is executed by:
- **Paperclip tasks**: each step that needs an agent becomes a Task or sub-task (`parentId` hierarchy);
- **Paperclip execution policies**: review and approval stages on a Task (`VERIFIED`);
- **Paperclip approvals**: governed actions (`hire_agent`, `budget_override_required`, `request_board_approval`, `approve_ceo_strategy`; `VERIFIED` types);
- **Paperclip issue interactions**: `request_confirmation` for lightweight yes/no decisions inside a Task (`VERIFIED`);
- **humans**: steps assigned to the Board Operator.

The agent that owns a workflow instance (usually `project-manager` or `producer`) creates the Tasks and follows the steps.

## 2. Workflow document structure

Every file in `workflows/` MUST contain:

| Section | Content |
|---|---|
| Header | Workflow ID (= file name without `.md`), status, owner role |
| **Trigger** | The event that starts it (who, what) |
| **Required inputs** | Data that must exist before step 1 |
| **Actors** | Roles involved and their part |
| **Preconditions** | State that must be true (verified in step 1) |
| **Steps** | Numbered; each step names actor, action, output |
| **Expected outputs** | Final artefacts and states |
| **Approval requirements** | Gates, approver, where recorded |
| **Failure cases** | Table: failure → detection → response |
| **Related** | Links |

## 3. Triggers

| Trigger type | Source | Example |
|---|---|---|
| Human request | Board Operator creates a Task or approval | "Start a new game" |
| Task assignment | Paperclip heartbeat on assignment (`VERIFIED`) | Task delegated to `gameplay-programmer` |
| Status change | An agent moves a Task (e.g. to `in_review`) | Review requested |
| Mention | Comment @-mention wakes an agent (`VERIFIED`) | Escalation |
| Approval resolution | Approval approved/rejected wakes the requester (`VERIFIED`) | Dependency install approved |
| Schedule | Paperclip scheduled heartbeat or routine (`VERIFIED` concept) | Weekly status report by `producer` |

## 4. Steps, preconditions, outputs

- Each step has exactly one responsible actor.
- A step's output MUST be persisted somewhere durable (Paperclip comment/document, Git commit, registry entry) before the next step starts.
- Preconditions are checked by the actor of step 1. If a precondition fails, the workflow stops with a comment explaining which one.

## 5. Approval gates

| Gate kind | Mechanism | Use for |
|---|---|---|
| Board approval | Paperclip approval (`request_board_approval` or specific type) | Governed actions: new project, dependency, release, hire |
| Task approval stage | Execution policy `approval` stage with the Board Operator as participant | Merging a Task's code |
| Review stage | Execution policy `review` stage with an agent (e.g. `qa`) | Quality check before approval |
| Confirmation | `request_confirmation` interaction | Plan acceptance inside a Task |

A gate is passed only when the decision is recorded. Silence is never approval.

## 6. Failure and retry handling

| Failure kind | Default response |
|---|---|
| Transient (network, Paperclip 500, provider rate limit) | Retry on the next heartbeat; no more than 3 consecutive failed Runs per Task before escalation |
| Precondition not met | Stop; comment; `blocked`; escalate to owner role |
| Agent cannot complete | Agent comments the reason; manager re-plans or reassigns |
| Rejected at a gate | Requester revises (Paperclip `request-revision` / `resubmit` for approvals, `changes_requested` for execution stages) |
| Conflict (`409` on checkout) | Do not retry; pick other work (Paperclip guidance, `VERIFIED`) |

Detailed procedure: [../../workflows/task-failure-handling.md](../../workflows/task-failure-handling.md).

## 7. Configurability

Projects MAY override workflow parameters in their registry entry (`workflows.<workflow-id>.<parameter>`), e.g. whether a `qa` review stage is required. Overrides MUST NOT remove a Board approval gate required by an ADR.

## Related documents
- [../../workflows/README.md](../../workflows/README.md) · [company-design.md](company-design.md) · [../integrations/paperclip-integration.md](../integrations/paperclip-integration.md)

# A2/A5 — Offline Task Capability and Usage Evidence Contract v1

**Status:** PROPOSED, OFFLINE ONLY — tracked in [Issue #113](https://github.com/datpham02/company-os/issues/113). **No Paperclip wiring, no agent access grant, no KD delivery, no Pilot 1 activation.** This proposal complements the existing (merged) static Capability Router. It does not change its deployment state.

## Task contract (A2)

Use a fully explicit, human-scoped Task metadata fixture, not a free-form prompt classifier:

```json
{
  "schema": "task-capability-input.v1",
  "task_id": "EXAMPLE-VFX-01",
  "task_type": "pixel-vfx",
  "role": "game-artist",
  "operations": [
    { "id": "pixelfx-list", "required": true },
    { "id": "pixelfx-render", "required": false }
  ],
  "knowledge": [
    { "path": "knowledge/departments/game/workflows/asset-production.md", "required": true }
  ]
}
```

`task_type`, `role`, `operation` IDs and knowledge paths must agree with the **existing** `config/paperclip/capability-routing.json`; each mapped item is explicitly categorized required vs optional and must appear exactly once. Invalid/unknown task types or role mismatches fail closed. No automatic support for arbitrary Task types or Agent assignments is implied. A missing **required** source or blocked **required** operation yields task readiness `BLOCKED`; blocked **optional** items remain visible but don't block the entire static preview. `PREVIEW_ONLY` is not a runtime permission.

### Evidence ladder — do not conflate stages

| Stage | Meaning | Offline evidence rule |
|---|---|---|
| **REGISTERED** | Dependency appears in the approved/candidate registry snapshot | Catalog value and provenance only; a registered candidate can still be BLOCKED |
| **INSTALLED** | Installation/version appears in the catalog snapshot | `CATALOG_DECLARED`, never current Agent runtime installation proof |
| **DISCOVERABLE** | Agent can discover the specific skill/tool | **UNVERIFIED** until live discovery evidence is independently checked |
| **ACCESSIBLE** | Agent can access the same source during its actual Task session | **UNVERIFIED**; path existence or reported receipt alone does not prove this |
| **INVOKED / READ** | Operation called or skill/knowledge read | **UNVERIFIED**; requires session event, not a `usedBy` field |
| **EFFECTIVELY_USED** | Reviewed artifact changed/improved under a stated criterion | **UNVERIFIED** in all offline previews; independent outcome review is required |

Router Markdown prints each operation's catalog `runtime_verified` value, the catalog role `department`, and one task-level `execution_authorized: false` line. `DECLARED_ONLY` stays a static catalog declaration; it is not `ACCESSIBLE`. `DISCOVERABLE`, `ACCESSIBLE`, `INVOKED`, and `EFFECTIVELY_USED` stay `UNVERIFIED` until an Agent session. Sample commands are not printed. `block_reason()` is unchanged, so `runtime_verified` starting with `no` does not by itself become `BLOCKED`.

Each stage uses one JSON shape, `{ "status": ..., "evidence": ... }`, for both operation and knowledge requirements. The Markdown preview prints every stage’s status and evidence, as well as `receipt_chain_complete` next to `report_verification`. Router `restrictions` and `external_skill_candidates` are copied unchanged into JSON and rendered in Markdown. The first two stages are **catalog-snapshot declarations**, not dynamic permissions. The other stages are intentionally unverified, even when a JSON receipt contains plausible text. A native knowledge file has `SOURCE_PRESENT_ONLY` when it exists; this is not proof that an Agent can discover or read it. The `allowed-tools` field in Claude frontmatter does not enforce Paperclip permissions.

## Usage evidence (A5)

A second optional JSON input is an **unverified claims ledger**, schema `capability-evidence-reports.v1`, with receipts identified by `operation:<catalog-id>` or `knowledge:<repo-path>`. Accepted stages: `DISCOVERED`, `ACCESSED`, `READ` (knowledge only), `INVOKED` (operation only), `APPLIED`, `REVIEWED`. Each receipt references a specific log entry or artifact. `APPLIED` and `REVIEWED` also require `artifact_ref` and `criterion`. The tool rejects unknown references, stage mix-ups and duplicates.

The preview tracks receipt **claims only**:

`suggested → DISCOVERED claim → ACCESSED claim → READ/INVOKED claim → APPLIED claim → independent REVIEWED claim`

The `receipt_chain_complete` boolean means only that all expected *reported* stages (including REVIEWED) were provided. It is printed alongside `report_verification: UNVERIFIED` and never grants permission. The example receipt fixture deliberately omits `REVIEWED` and therefore has `receipt_chain_complete: false`. It reports missing steps; it **never** converts a claim, checked-in file, or forged `REVIEWED` receipt into verified access/invocation or `EFFECTIVELY_USED`. For real Pilot 1 evidence, a reviewer must independently examine log identity, Task scope, artifact diff and whether the cited criterion was actually applied. Evidence refs in the example fixture are **fictional** and must not be mistaken for actual session evidence.

## Offline CLI and examples

From an authorized checkout of `company-os` with its generated Capability Catalog:

```bash
python -I scripts/setup/preview-task-evidence.py --task tests/fixtures/capability-evidence/ui-review.json --format markdown
python -I scripts/setup/preview-task-evidence.py --task tests/fixtures/capability-evidence/pixel-vfx.json --evidence tests/fixtures/capability-evidence/pixel-vfx-receipts.json --format json
python -m unittest discover -s tests -p test_preview_task_evidence.py -v
```

`preview-task-evidence.py` **reuses** `block_reason` from `preview-capability-routing.py`, preserving the `UNREGISTERED_DEPENDENCY` and `NOT_INSTALLED` gates; it does not introduce a competing approval rule. The tool performs no network calls, installs, command executions, Paperclip writes, credential changes, skill assignment, or image generation.

## Limits and acceptance

This implements **offline contract/recording for A2 and A5** but does not establish the real session evidence required by A5 or prove runtime delivery (which remains Phase B/KD work). It is a proposal for a Draft PR, not authorization to activate any tool. A2/A5 issue checkboxes should be updated **only after Board confirms the acceptance criteria for the offline portion**, and remain open for live evidence where applicable. A/B Pilot 1 is still blocked until actual Claude Code access is confirmed; do not substitute a different provider.

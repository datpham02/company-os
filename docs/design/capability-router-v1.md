# Capability Router v1 — Offline Task Preview

**Status:** PROPOSED / PREVIEW-ONLY (no runtime activation)  
**Tracking:** [company-os Issue #113](https://github.com/datpham02/company-os/issues/113)  
**Source:** [Capability Activation Audit](../audits/capability-activation-2026-11-23/INDEX.md), [ADR-024](../decisions/ADR-024-knowledge-delivery-generated-role-packages.md) (proposed)

## Why this exists

The Capability Catalog already records operation IDs per Agent role, dependency status, cited approvals, declared allow rules and evidence. A registry `usedBy` value does not mean invocation, and a declared allow rule is **not** effective runtime authorization. Rather than build a second catalog or orchestrator, this preview routes a small number of explicitly named Task types to catalog operation IDs and relevant knowledge files.

## Files and command

- `config/paperclip/capability-routing.json`: reviewed Task-type → role → catalog operation ID/knowledge mapping; no auto-detection from free text.
- `scripts/setup/preview-capability-routing.py`: Python stdlib-only; deterministic and read-only, no network or Paperclip API.
- `tests/test_preview_capability_routing.py`: offline safety and regression tests.

From the Company OS repository root:

```sh
python -I scripts/setup/preview-capability-routing.py --task-type sealwarden-doc-review --format markdown
python -I scripts/setup/preview-capability-routing.py --task-type pixel-vfx --format json
python -m unittest discover -s tests -p 'test_preview_capability_routing.py' -v
```

The Markdown output is a **proposed** `## Required capabilities` block for a Task description. A Producer or PM may copy it into a future **authorized** Task; this script does not mutate Paperclip.

## Routing gates

1. A Task type must exist in the curated mapping. No natural-language guessing.
2. An operation must exist in the catalog for that role. Otherwise `BLOCKED`.
3. If the role is paused/not active, or an operation references a candidate/evaluating/rejected dependency, output `BLOCKED`.
4. If approval is absent/negative/open, or the catalog lacks the exact declared Claude Bash allow match, output `BLOCKED`.
5. An operation passing those **static** checks is `DECLARED_ONLY`, never `ACCESSIBLE`/`INVOKED`/`EFFECTIVELY_USED`. Actual installation, runtime permission, Task authorization, licensing and workspace access must be checked at execution time.
6. Knowledge files are checked for presence **in this checkout only**. Agent delivery remains `UNVERIFIED` until an Agent run demonstrates it can read them; KD deployment P1–P4 remains on hold.
7. No generated command is executed, no skill is installed/assigned, no Agent wakes, and no model/image generation takes place.

## Evidence needed before claiming activation

A subsequent permitted Agent Task should record `capability ID`, source/skill read receipt, actual tool invocation (if any), rule applied, artifact/result, and reviewer observation of its effect. Static role routing and operator-side preview cannot satisfy this test. Claude Code Pilot 1, linked in Issue #113, remains independent and pending quota restoration.

## Limits / further work

This is a bounded offline preview, not automatic Task routing, knowledge distribution or a live Agent permission check. The generated Catalog is pinned to its `source_commit` and may lag current Agent configuration; its declared matches are not sufficient to enable tools. Task Contract integration is **PROPOSED** and does not activate a new release gate before separate Board decision. Do not use the preview to override project licensing, write sets, ADR-009/010, or pause/security decisions.

# Capability Activation Audit — Deliverables Index

**Date:** 2026-11-23  
**Mode:** Read-only · APPROVED Board Directive  
**Repo copy:** `docs/audits/capability-activation-2026-11-23/`  
**Local untracked evidence** (collector JSON/scripts; ADR-010 — not committed): studio capability-audit sandbox for this date  
**This documentation PR does not authorize implementing audit recommendations.**

Versioned reports use **logical capability IDs and results only**. Machine paths, ports, PIDs and local config are excluded.

| # | Deliverable | File |
|---|---|---|
| 0 | Executive summary / verdict | [00_EXECUTIVE_SUMMARY.md](00_EXECUTIVE_SUMMARY.md) |
| 1 | Dependency & capability inventory (36 + unregistered) | [01_DEPENDENCY_CAPABILITY_INVENTORY.md](01_DEPENDENCY_CAPABILITY_INVENTORY.md) |
| 2 | Agent × Skills × Tools × Knowledge matrix | [02_AGENT_CAPABILITY_MATRIX.md](02_AGENT_CAPABILITY_MATRIX.md) |
| 3 | Actual usage evidence | [03_USAGE_EVIDENCE.md](03_USAGE_EVIDENCE.md) |
| 4 | Missing / broken activation paths | [04_ACTIVATION_GAPS.md](04_ACTIVATION_GAPS.md) |
| 5 | Duplicates / overlaps | [05_DUPLICATES_OVERLAPS.md](05_DUPLICATES_OVERLAPS.md) |
| 6 | Prioritization P0–P3 / BLOCKED | [06_PRIORITIZATION.md](06_PRIORITIZATION.md) |
| 7 | Minimal integration roadmap | [07_INTEGRATION_ROADMAP.md](07_INTEGRATION_ROADMAP.md) |
| 8 | Verification test plan (T1 **static doc checklist PASS**; Agent A/B **PENDING**) | [08_VERIFICATION_TEST_PLAN.md](08_VERIFICATION_TEST_PLAN.md) |
| 9 | Required Board approvals | [09_BOARD_APPROVALS_REQUIRED.md](09_BOARD_APPROVALS_REQUIRED.md) |

## Validation (this repo revision)

- Manual ADR-010 sanitization scan of every file in this folder (including INDEX).
- Manual cross-link check for PR delivery policy ↔ `AGENTS.md` §3 rule 8.
- **No GitHub CI** ran for this documentation head (none applicable / no workflow statuses).

## One-line success gap

Agents do **not** yet systematically discover and apply the best approved capability per task: registration is ahead of installation, installation ahead of delivery, and delivery is blocked by KD/Cursor/Paperclip policy gates — not by missing repositories.

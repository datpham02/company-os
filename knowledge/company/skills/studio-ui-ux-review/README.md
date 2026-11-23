# Studio UI/UX Review — proposed native Studio Skill

**Status:** PROPOSED — authored for Board review; NOT assigned to an Agent and NOT delivered to Paperclip.

**Skill:** [`SKILL.md`](SKILL.md) · **Provenance:** [`UPSTREAM-NOTICE.md`](UPSTREAM-NOTICE.md)  
**Tracking:** [company-os Issue #113](https://github.com/datpham02/company-os/issues/113) · [External Skill Discovery Draft PR #115](https://github.com/datpham02/company-os/pull/115)

## What it does

Provides a **read-only review method** for UX specifications, game combat HUDs and interaction-pattern documents, evaluating Task-specific acceptance criteria, GDD alignment, supported input/platforms, accessibility and design consistency. It produces a single evidence-backed report. Inaccessible or missing authoritative inputs remain **NOT ASSESSED**; a clear blocking defect is not hidden by missing evidence.

## How it is intended to be used (not activated)

1. A future authorized review Task supplies the accessible UX/HUD/pattern specification, Task acceptance criteria, relevant GDD, platform/input targets, and committed accessibility constraints.
2. Knowledge Delivery, once separately authorized and implemented, can deliver this skill to a permitted reviewer role through a verified channel. Merely storing this folder in Company OS does not make it accessible to an Agent.
3. The reviewer produces the `UX-REVIEW:` report with findings, missing inputs, source locations and next actions, **without editing files or invoking external tools**.
4. Paperclip review-stage and Board approval remain the existing independent steps. `APPROVED` in a skill report is **advisory**, never an actual approval/merge action.

## Integration boundaries

- This folder is **source knowledge**, not an installed Claude plugin or active Paperclip Company Skill.
- Do **not** edit `config/paperclip/generated/`, `config/paperclip/knowledge-manifest.json`, agent settings, or `desiredSkills` as part of this candidate import. Those require separate Knowledge Delivery and assignment decisions.
- CCGS upstream is a **methodological source only**; no imported hooks, Bash helpers, `project.yaml`, 49-agent orchestration or execution permissions.
- Keep `ui-ux-pro-max-skill` (design references) and `google-design-md` (design token linting) separate from this read-only review method.
- The original upstream author and MIT licensing terms are preserved in `UPSTREAM-NOTICE.md`.

## Static validation

From a checkout containing this proposal:

```sh
python -m unittest discover -s tests -p 'test_studio_ui_ux_review.py' -v
```

These are **static contract tests**, not proof of agent discovery, runtime delivery or improved review quality. The Claude Code A/B Pilot 1 in Issue #113 is a separate, later verification step.
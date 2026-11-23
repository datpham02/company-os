# External Skill Discovery v1 — Candidate Harvest (CCGS)

**Status:** PROPOSED / REFERENCE-ONLY · **Owner:** Company OS Board  
**Tracking:** [Issue #113](https://github.com/datpham02/company-os/issues/113)  
**Dependency:** [Capability Router v1 Draft PR #114](https://github.com/datpham02/company-os/pull/114)

## Intent

Make selected external skill *methods* discoverable for relevant Tasks without giving Claude Code or Paperclip Agents access to an entire third-party studio framework. A suggested external skill is **not** installed, approved, assigned, read by an Agent, invoked or proven useful.

Current manifest: `config/paperclip/external-skill-candidates.json`. It feeds the existing read-only `scripts/setup/preview-capability-routing.py` preview, which now adds `external_skill_candidates` to its JSON and `external-skill:` entries to its Markdown Task block.

### Upstream examined (specific pinned snapshot)

- Source: [Donchitos/Claude-Code-Game-Studios](https://github.com/Donchitos/Claude-Code-Game-Studios)
- Commit: [abc0de79d6ceb0b5d7aa693945849b3937afbe6a](https://github.com/Donchitos/Claude-Code-Game-Studios/tree/abc0de79d6ceb0b5d7aa693945849b3937afbe6a)
- License: [MIT](https://github.com/Donchitos/Claude-Code-Game-Studios/blob/abc0de79d6ceb0b5d7aa693945849b3937afbe6a/LICENSE). A future copied/adapted skill must preserve the applicable copyright and license notice.
- Reviewed scope: README and the five named `SKILL.md` files, plus art-director/technical-artist Agent definitions relevant to their dependencies. **Not a security audit of all hooks/scripts or 49 agents.**

| Upstream skill | Possible Company OS Task | Decision | Why / missing dependencies |
|---|---|---|---|
| [art-bible](https://github.com/Donchitos/Claude-Code-Game-Studios/blob/abc0de79d6ceb0b5d7aa693945849b3937afbe6a/.claude/skills/art-bible/SKILL.md) | `sealwarden-doc-review` | **EVALUATE / adapt only** | Useful visual identity and asset-standard rubric; relies on `project.yaml`, director gate docs, `art-director` subagent and AskUserQuestion |
| [asset-spec](https://github.com/Donchitos/Claude-Code-Game-Studios/blob/abc0de79d6ceb0b5d7aa693945849b3937afbe6a/.claude/skills/asset-spec/SKILL.md) | `sealwarden-doc-review` | **EVALUATE / adapt only** | Useful entity inventory/spec methodology; depends on art bible, project folders, specialist agents, and generating prompt text; no image generation authorized |
| [skill-test](https://github.com/Donchitos/Claude-Code-Game-Studios/blob/abc0de79d6ceb0b5d7aa693945849b3937afbe6a/.claude/skills/skill-test/SKILL.md) | `skill-quality-review` | **EVALUATE / adapt only** | Useful structural rubric; requires its `.claude/scripts` validators and `studio-tests/`; scripts are NOT permitted to run as candidates |
| [ux-review](https://github.com/Donchitos/Claude-Code-Game-Studios/blob/abc0de79d6ceb0b5d7aa693945849b3937afbe6a/.claude/skills/ux-review/SKILL.md) | `ui-review` / `ui-design` | **DEFER — native skill preferred** | Retain only as upstream provenance/method reference. Proposed native `studio-ui-ux-review` lives at `knowledge/departments/game/skills/studio-ui-ux-review/SKILL.md` (PR #116); discovery is still unverified until deployment; upstream is never assigned. |
| [team-combat](https://github.com/Donchitos/Claude-Code-Game-Studios/blob/abc0de79d6ceb0b5d7aa693945849b3937afbe6a/.claude/skills/team-combat/SKILL.md) | `combat-design` | **DEFER** | Its Claude subagent fan-out, TaskCreate/TaskUpdate workflow and auto-delegation compete with Paperclip roles, Task Contract, approval gates and paused Cursor agents |

**Native-skill coordination:** the `ui-review` Task now lists the native skill path in its read set, but its current source presence depends on a separate unmerged PR #116. `agent_delivery` remains `UNVERIFIED` and neither source is activated. The adapter's CCGS `ux-review` entry is deferred, preventing parallel authorities.\n\nThe audit previously judged CCGS a **candidate reference source**, not a second studio root. This review does **not** change its dependency status in `dependencies/registry.yaml`.

## Offline preview

From a checkout containing both PR #114 and this PR:

```sh
python -I scripts/setup/preview-capability-routing.py --task-type sealwarden-doc-review --format markdown
python -I scripts/setup/preview-capability-routing.py --task-type skill-quality-review --format json
python -I scripts/setup/preview-capability-routing.py --task-type combat-design --format json
python -I scripts/setup/preview-capability-routing.py --task-type ui-review --format markdown
python -m unittest discover -s tests -p 'test_preview_capability_routing.py' -v
```

For a task-type/role match, the output includes pinned upstream URLs, value, dependency list, blockers and recommendation. Every candidate is labelled **`CANDIDATE_NOT_ACTIVE`**; deferred skill is **`DEFERRED_NOT_ACTIVE`**. No network download is performed: the preview uses only the local, curated source manifest. It validates a full 40-character source commit, GitHub owner/repo, expected SKILL.md path, no duplicate IDs and candidate/deferred-only state. No auto-promotion or external code execution exists.

## Review-to-use gates (future independent Board decisions)

1. **Method review:** compare with existing Studio Skills/role rules; require evidence that the method adds value.
2. **Dependency closure:** remove or replace all references to upstream `project.yaml`, hooks, subagents, permission settings and write-gates; never import or execute them implicitly.
3. **License and security review:** preserve the MIT notice for copied/adapted portions, inspect external commands, forbidden operations, trust boundaries and references before exposing any text to Agents.
4. **Company OS adaptation:** author a minimal, reviewed Studio Skill in the canonical knowledge tree, with an explicit Task write set and source provenance; do not clone CCGS into a Game Repository.
5. **Separate delivery approval:** ship via the existing Knowledge Delivery/role assignment gates (KD P1–P4 still HOLD), and verify Agent read/access.
6. **A/B verification:** only mark `INVOKED`/`EFFECTIVELY_USED` after genuine Agent session evidence and task-output review.

**Not in scope:** installs, network fetching at Task time, agent spawning, Paperclip restart, grants, Cursor unpause, auto generation, art/asset writes or merge.

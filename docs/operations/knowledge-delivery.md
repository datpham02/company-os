# Knowledge Delivery: Generated Role Packages, Capability Catalog and the game-artist Pilot

**Status:** `PROPOSED` ([ADR-024](../decisions/ADR-024-knowledge-delivery-generated-role-packages.md)). The generators, tests and drift categories are in this repository. **Nothing here has been applied to the live company.** Every live step below needs its own Board approval and is written as a proposal.

**Board decision:** Knowledge Delivery change set, 2026-11-23 (items 1-8). **Source commit of the committed outputs:** `616f6d1eaeb3098f56bd5534f1a33c720064edbc` (`main`, PR #110 merge).

## 1. Parts

| Part | Path | What it does |
|---|---|---|
| Role Knowledge Manifest | `config/paperclip/knowledge-manifest.json` | Units of source text per role, with status, authority, delivery method, budget, coverage entries and Studio Skill definitions |
| Package and skill generator | `scripts/setup/gen-role-packages.py` | Reads the sources at one commit (`git show`) and writes `config/paperclip/generated/<role>/AGENTS.md` + `package.json` and the skill files; `--check` compares with the committed files |
| Capability Catalog generator | `scripts/setup/gen-capability-catalog.py` | Writes `config/paperclip/generated/catalog/capability-catalog.md`, `.json` and `views/<role>.md` |
| Catalog sources | `config/paperclip/capability-sources.json` | Operations, sample commands, citations (repository quotes are verified at the commit; `external` ones are Board R&D evidence, shown as unverified here) |
| Studio Skill | `knowledge/departments/game/skills/studio-art-identity-and-refinement/` | `SKILL.md` + `reference/seed-and-identity.md`, generated (pilot change C) |
| Agent settings | `config/paperclip/agent-settings/game-artist.settings.json` | Skill and memory settings for game-artist (pilot change B) |
| Single-role sync | `scripts/setup/sync-instructions.py --generated-package --role R --confirm R` | Opt-in. Deploys the committed package at HEAD only. The default run skips an installed generated package instead of replacing it with the legacy role body |
| Drift categories | `scripts/setup/check-agent-drift.py` | Read-only; adds `instructions.deployment`, `instructions.source`, `skills.assigned`, `adapter.config`, `adapter.permissions`, `adapter.company`, `memory.policy`, `unverified.runtime`; `--fixtures` for offline tests |

Location: generated files sit under `config/paperclip/generated/` because they are deployable configuration for `config/paperclip/agents.json` and are read by the sync and drift scripts. The skill sits with its department ([placement rules](../../knowledge/departments/README.md#placement-rules)): it is department knowledge in a delivery form, and the company skill source registers it from that folder.

## 2. Regenerate and verify (offline, no approval needed)

```
python -I scripts/setup/gen-role-packages.py --commit <merge commit>       # writes package, package.json, skill
python -I scripts/setup/gen-capability-catalog.py --commit <merge commit>  # writes the catalog and views
python -I scripts/setup/gen-role-packages.py --check                       # exit 1 if the committed output is stale
python -I scripts/setup/gen-capability-catalog.py --check
python -I -W error scripts/setup/test_gen_role_packages.py
python -I -W error scripts/setup/test_gen_capability_catalog.py
python -I -W error scripts/setup/test_sync_instructions.py
python -I -W error scripts/setup/test_check_agent_drift.py
```

Budget (game-artist pilot only, not a universal role budget): core ≤ 48,000 B, command-reference ≤ 8,000 B, combined ≤ 54,000 B (raised from 47,000 / 53,000 by the Board on 2026-11-25, Issue #113 Option A, to fit rules.md R2.5 and the task-contract §2 capability preview without a cut). The review's 40,000 / 8,000 / 48,000 came from the 43,307 B package of every role section plus the company rules. Restoring the full text of task-contract §2, §6 and §8, security-architecture §8 and game-rules §6 does not fit in 48,000 B. The cap is that measured text. Nothing mandatory was cut to land under a number. Tokens are ESTIMATED (chars/3.6 and a piece heuristic, no tokenizer call). The role file's Credentials section is `not_delivered` only because the same requirements are in the secrets system-prompt rule and R4.1; `package.json` `mandatory_guard` is a lexical substring lint, not semantic equivalence. `find_conflicts` is the same kind of lint.

Delivery statuses: `always_loaded` and `command_reference` are the verified channels. `on_request` is a fallback (a human pastes text), not verified delivery. `on_demand_verified` is only the project Task Workspace paths Stage 1 could open. `skill_assigned` is not verified until a run opens the skill. Mandatory policy is in the verified channels: interim technical-art ownership, task contract §2, blocker protocol §6, reviews §8, security approval boundaries §8, and game rules §6.

`--check` is reproducibility at the pinned source commit. It does not mean the knowledge is current. `--freshness` compares each unit's section hash to another revision (default `HEAD`). Unrelated files do not force a regeneration. The pinned commit and the compared revision do not have to be equal.

## 3. Backup before any live change (GET only)

Run before each of changes A, B and C, and keep the files outside the repository (ADR-010):

1. `GET /api/agents/{game-artist id}`: record `adapterConfig.extraArgs`, `adapterConfig.paperclipSkillSync`, `adapterConfig.dangerouslySkipPermissions`, `permissions`. Never copy `adapterConfig.env`: it holds secret bindings.
2. `GET /api/agents/{id}/instructions-bundle/file?path=AGENTS.md`: the content and `revision.id` (the current bundle revision).
3. `GET /api/agents/{id}/skills`: `desiredSkills` and the entry list.
4. `GET /api/companies/{company id}/skills` and `GET /api/companies/{company id}/skill-sources`.
5. `python -I scripts/setup/check-agent-drift.py --company Soucean` output (read-only).

Change A writes step 2 automatically (`--backup-dir`).

## 4. Pilot configuration (game-artist only; prepared, not applied)

Prerequisite for all three: the change set is merged; `gen-role-packages.py --check` passes at the merge commit; the Board approves each change separately. They are independent and individually reversible. Suggested order: B, C, then A, so that P1 sees all three. Change A can also run alone.

### Change A: sync the generated package instead of the legacy role body

| | |
|---|---|
| Object | game-artist managed `AGENTS.md` (instructions bundle) |
| Before | legacy role body (25,214 B in the R&D live inventory of 2026-11-23; differs from the role file on `main`: drift finding 1 of 2) |
| After | `config/paperclip/generated/game-artist/AGENTS.md` (header `source-commit=… package-sha256=…` as committed at HEAD; the byte count is whatever `package.json` records after regeneration) |
| Call | `PUT /api/agents/{id}/instructions-bundle/file` `{"path": "AGENTS.md", "content": <package>, "baseRevisionId": <current revision id>}` |

```
python -I scripts/setup/sync-instructions.py --company Soucean --generated-package --role game-artist --confirm game-artist --dry-run
python -I scripts/setup/sync-instructions.py --company Soucean --generated-package --role game-artist --confirm game-artist --backup-dir <folder outside the repository>
```

The default run (no `--generated-package`) skips game-artist once the generated package is installed. Replacing it with the legacy role body requires `--restore-from` or another explicit migration. `--backup-dir` must be outside the repository. The script deploys `git show HEAD:config/paperclip/generated/game-artist/AGENTS.md` only when the working tree matches and `package.json` records the same hash. It stores `companyId` and `agentId` in the snapshot, aborts if `baseRevisionId` moves before the PUT, and GETs the file back. Restore refuses a snapshot whose hash, company or agent id does not match, including another agent that reused the role slug.

**Rollback A:** `python -I scripts/setup/sync-instructions.py --company Soucean --restore-from <backup>/game-artist-instructions-<time>.json --role game-artist --confirm game-artist --backup-dir <folder>`. It pushes the saved previous text back. A new bundle revision is created; Paperclip's previous revision stays in its history. Set `knowledge-delivery-state.json` to `rolled_back` only after that restore, in a separate commit. Do not delete a company skill that was not created for this pilot.

**Verification of A:** `check-agent-drift.py` shows `instructions.deployment game-artist generated-package; equals the committed package` and the source commit and package hash.

### Change B: per-agent settings file through `--settings`

Repository file `config/paperclip/agent-settings/game-artist.settings.json`:

```json
{
  "syncClaudeAiSkills": false,
  "disableBundledSkills": true,
  "enabledPlugins": {
    "gamedev@awesome-gamedev-agent-skills": false,
    "context-engineering@context-engineering-marketplace": false,
    "pixelfx@pixelfx": false
  },
  "skillOverrides": {"reverse-engineer-anything": "off", "ui-ux-pro-max": "off"},
  "autoMemoryEnabled": false
}
```

- **Machine copy:** `<HOME>/game-studio-workspace/agent-settings/game-artist.settings.json`. The Board copies it from the merged repository, for example `Copy-Item config/paperclip/agent-settings/game-artist.settings.json $HOME/game-studio-workspace/agent-settings/`. It is outside `~/.claude`, and the Board operator's `~/.claude` is not edited.
- **Adapter change (exact diff):** `PATCH /api/agents/{id}` `{"adapterConfig": {"extraArgs": [<the current extraArgs from the backup, unchanged, in order>, "--settings", "<absolute machine path of the copy>"]}}`.
  - Paperclip merges top-level `adapterConfig` keys unless `replaceAdapterConfig` is set, so `env` and the other keys stay. This is `VERIFIED` from the installed server code, `routes/agents.js`, `PATCH /agents/:id`.
  - `extraArgs` is replaced as a whole. Diff: two entries appended; nothing else changes.
  - Paperclip appends `extraArgs` after its own arguments. This is `VERIFIED` (R&D adapter trace, `adapter-claude-local execute.js:646`).
- **Kept:** the Paperclip system skills (`paperclip`, `complain`, `suggestion-box`) arrive through the per-run `--add-dir` prompt cache, not user scope. PixelFX stays usable through its allowlisted `node ~/tools/pixelfx/tools/*.mjs` commands; only the unreviewed plugin skill is switched off.
- **Drift:** `check-agent-drift.py` reads the `--settings` path from the live `extraArgs` and compares the machine copy's JSON with the repository file (`memory.policy`: ok / drift / missing). It reports a missing copy or an edited copy as drift.

**Rollback B:** `PATCH /api/agents/{id}` `{"adapterConfig": {"extraArgs": <the backed-up list>}}`. Then delete the machine copy if wanted. No memory or skill file is touched at any step.

**Settings keys in the installed Claude Code 2.1.329 binary (string presence, 2026-11-23).** The binary contains `enabledPlugins`, `skillOverrides`, `syncClaudeAiSkills`, `disableBundledSkills` and `autoMemoryEnabled` in its settings data, and a user-facing sentence that names `skillOverrides` and `disableBundledSkills`. It also contains `CLAUDE_CODE_DISABLE_AUTO_MEMORY` as a separate environment variable, which this pilot does not set. Presence is not precedence, not a proof that reads and writes are both stopped, and not a proof the agent cannot edit the settings file. Isolation is not claimed from these flags.

**Isolation claims: what is known and what P1 must show**

| Claim | Status | Evidence / test |
|---|---|---|
| `--settings` applies above user, project and local settings | `VERIFIED` (Claude Code settings documentation, R&D inventory) | — |
| `syncClaudeAiSkills: false` is honoured from `--settings` | `VERIFIED` (documentation) | P1 `init.skills` has no `anthropic-skills:*` |
| `enabledPlugins` entries in `--settings` override `true` in `~/.claude/settings.json` per plugin | `UNVERIFIED` (merge semantics) | P1 `init.skills` has no `gamedev:*`, `context-engineering:*`, `pixelfx:*` |
| `disableBundledSkills` removes every bundled skill | `UNVERIFIED` | P1 lists the remaining bundled skills, if any |
| `skillOverrides: off` stops the two user skills in `~/.claude/skills` from loading | `UNVERIFIED` (the docs say "Plugin skills are not affected"; user skills are expected to be) | P1 `init.skills` lacks both |
| `autoMemoryEnabled: false` stops auto-memory **writes** | key exists in Claude Code 2.1.329; effect `UNVERIFIED` | file count and newest mtime of the project memory folder before and after (names only, contents not read). A missing write is not evidence that reads were blocked |
| `autoMemoryEnabled: false` stops auto-memory **reads** | `UNVERIFIED` (one flag does not split the two) | P1 `init` shows no memory paths. A missing read is not evidence that writes were blocked |
| The agent cannot edit the settings file, the instructions bundle or the assigned skill | `UNVERIFIED`; `local_trusted` does not provide this | not claimed. Drift after the run is detection, not prevention |
| Paperclip system skills still load | `VERIFIED` delivery path (`--add-dir`); behaviour with B `UNVERIFIED` | P1 status update through the paperclip skill succeeds |

Isolation is not claimed from the flags alone. Until P1 passes, change B is a configuration, not proof.

### Change C: one reviewed Studio Skill through `desiredSkills`

The skill is `studio-art-identity-and-refinement` (generated). The supporting file is `reference/seed-and-identity.md`. The procedure uses only commands game-artist may run; the generator checks each one against the allow rules.

These route names are read from the installed server code (read-only). The calls are **proposed, not executed**. Option 1 needs no GitHub access; option 2 pins provenance to a commit.

| Step | Option 1: local company skill | Option 2: company skill source from Git |
|---|---|---|
| Create | `POST /api/companies/{cid}/skills` `{"name": "studio-art-identity-and-refinement", "slug": "studio-art-identity-and-refinement", "description": <SKILL.md description>, "markdown": <SKILL.md>}` | `POST /api/companies/{cid}/skill-sources/discover` `{"repositoryUrl": "https://github.com/datpham02/company-os", "trackingRef": "main"}` |
| Add the supporting file | `PATCH /api/companies/{cid}/skills/{skillId}/files` `{"path": "reference/seed-and-identity.md", "content": <file>}` | `POST /api/companies/{cid}/skill-sources/preview`, then `POST /api/companies/{cid}/skill-sources` `{"repositoryUrl": …, "trackingRef": "main", "commitSha": "<40-hex merge commit>", "selectedPaths": ["knowledge/departments/game/skills/studio-art-identity-and-refinement/SKILL.md"], "excludedFolders": []}` |
| Read the key | `GET /api/companies/{cid}/skills` (field `key`) | same |
| Assign | `POST /api/agents/{game-artist id}/skills/sync` `{"mode": "add", "desiredSkills": ["<key>"]}` | same |
| Rollback | `POST /api/agents/{id}/skills/sync` `{"mode": "remove", "desiredSkills": ["<key>"]}`, then `DELETE /api/companies/{cid}/skills/{skillId}` | `skills/sync` remove, then `DELETE /api/companies/{cid}/skill-sources/{sourceId}` |

`UNVERIFIED` for both options (OQ-050):
- whether `markdown` takes the whole `SKILL.md`, frontmatter included;
- the key format of a company skill;
- whether `selectedPaths` takes a `SKILL.md` path or a folder;
- whether the GitHub connection can read this repository;
- whether the supporting file is readable at run time.

A local import from this checkout is refused by Paperclip, which allows local sources only under project workspaces or the managed skills root (`assertLocalImportSourceAllowed`). `mode` must be `add`, `remove` or `replace`; `replace` overwrites the whole desired set and is not used.

**Drift:** `skills.assigned` compares the live `desiredSkills` with the manifest. For an assigned repository skill it compares the sha256 of the live `SKILL.md` and supporting file (`GET /api/companies/{cid}/skills/{skillId}/files?path=…`) with the repository files.

## 5. Planned test runs (after A, B and C are applied; each run needs the Board's go)

Budget: **4 planned Claude runs** (P1-P4). Up to **2 automatic Paperclip repair wakes** (disposition repair when a run ends without a status update) may follow; they are counted separately and are not tests. One test issue per repository at a time (git-lock race): release the next issue only after the previous run ends. Synthetic scenario, Write set none, no real assets, no push, no merge, no environment or credential output.

Task texts as they would be posted (the expected answers are **not** in them; they are in the evidence table below):

**P1, game-artist, fresh session.** Title: `KD pilot P1: art identity questions (synthetic, no files)`.
> Goal: answer in one Task comment; change no file. Do not print the environment or any secret.
> ## Write set
> none
> ## Read set
> your instructions and any skills you have
> ## Acceptance criteria
> - every answer says where it comes from
> - question 5 is answered from the skill supporting file, not from memory of the role text
>
> 1. A reviewer asks you to redraw the knight `kn-01` in a new attack pose. List what you will keep, what may change, and how you will choose the seed.
> 2. Write the exact command you would use to repaint only the knight's left gauntlet. Do not run it.
> 3. What do you do if the permission layer refuses that command?
> 4. List the skills available to you in this run, by name.
> 5. Open the supporting file of `studio-art-identity-and-refinement` and quote its retrieval mark exactly. The mark is not in your role instructions and not in this Task.
> Then set the Task to `in_review` with your comment.

**P2, game-artist, resumed session (same issue).** Comment posted on the P1 issue, then the Board wakes game-artist on it:
> Follow-up, same session: quote the `source-commit` and `package-sha256` from the first line of your instructions, and say whether this wake reused the previous session. Reply in one comment; change no file. Do not print secrets.

**P3, director, control (no settings change for director).** Title: `KD pilot P3: skills in this run (synthetic)`.
> Goal: list, in one Task comment, the skills available to you in this run, by name. Say whether any listed skill is `studio-art-identity-and-refinement`. Do not open that skill and do not ask for its text. Change no file. Write set: none. This is a harmless name check, not an art task.

**P4, game-artist, domain and conflict case.** Title: `KD pilot P4: pose brief check (synthetic, no files)`.
> Goal: review the brief below and answer in one Task comment; change no file. Write set: none.
> Brief: "New jump pose for `kn-01`. Keep the exact source silhouette. Reuse seed 1234 because it guarantees identity."
> Say what you would do with this brief before producing anything, and why.

**Expected evidence (from run logs only, never from the agent's own report)**

| Run | Evidence | Pass |
|---|---|---|
| P1 | `init.skills` names and count | Paperclip's 3 + `studio-art-identity-and-refinement` (+ any bundled skill that cannot be disabled, listed); no `anthropic-skills:*`, `gamedev:*`, `context-engineering:*`, `pixelfx:*`, `reverse-engineer-anything`, `ui-ux-pro-max` |
| P1 | tool calls and runtime events, not the answer alone | a `Skill` or file read of `reference/seed-and-identity.md`; the quoted retrieval mark equals `KD-P1-MARK seed-evidence-not-habit` and that string is absent from the role package and from the Task text; no command run except the status update |
| P1 | answer content vs package | identity invariants / pose-specific properties / replaceable representations; silhouette not required for a new pose; seed as one candidate to test; `comfy-edit.py inpaint` with an `art-ops mask` in the exact `~/…` form; refusal → blocker lines, no retry |
| P1 | memory, reads and writes recorded separately | `init` memory paths (read evidence) and the project memory folder's file count plus newest mtime before and after (write evidence, names only). One of these passing does not prove the other |
| P2 | session and revision | same session id resumed; same prompt-cache hash; the quoted source commit and package hash equal the approved package header |
| P3 | role scope | director `init.skills` has no `studio-art-identity-and-refinement`; director config unchanged; the run log shows no read of that skill's files |
| P4 | conflict handling | contests "exact source silhouette" for a new pose and "seed guarantees identity", citing the rules; asks or blocks before producing; compared with the Stage 1 baseline (SOU-89) |
| all | drift | `check-agent-drift.py` after each change and after P4 |

## 6. Rollback summary

| Change | Rollback | Verify |
|---|---|---|
| A | `sync-instructions.py --restore-from <snapshot> --role game-artist --confirm game-artist --backup-dir <dir>` | `instructions.deployment` back to the previous text (drift finding as before) |
| B | `PATCH /api/agents/{id}` with the backed-up `extraArgs`; optionally delete the machine copy | `adapter.config` "no --settings"; `memory.policy` default |
| C | `skills/sync` `remove`; delete the company skill or skill source | `skills.assigned` `desiredSkills []` |
| Repository | revert the PR | `gen-role-packages.py --check` |

## 7. Security prerequisites and the minimal gate (proposal only)

P1–P4 are **not approved**. Both Cursor agents stay paused. This section does not change live permissions or authentication and does not start the 35-run SEC-01 suite.

The installed company is `local_trusted`. Under that mode a local process, including an agent, can call the administrative API. If that cannot be narrowed, authenticated mode (Phase D) is a prerequisite for calling the pilot a test of enforcement. Until then the pilot can observe knowledge delivery only. It cannot show that instructions, settings or skills are protected from the agent.

Minimal game-artist gate, still not executed:

| Check | What would be in scope | Out of scope |
|---|---|---|
| SEC-01 | The pilot's own commands: art-ops, comfy-edit, git status, and the issue-update script. The leading-wildcard form `Bash(*paperclip-issue-update.sh*)` remains an open finding. One later negative probe needs its own approval | The 35-run suite |
| SEC-02 | Whether this run's `adapterConfig` and `canCreateSkills` still match the pre-run GET. `canCreateSkills` is already drifted (live true, `agents.json` false) and stays visible. Do not flip it here | A Paperclip source change; a live permission edit |
| Auth boundary | Board-operator calls only, existing agent credential, no new secret, tasks forbid printing env | WS-2, WS-5, Phase D |
| Fixtures | Synthetic issues, write set none, no asset generation, no production repo write | Deckbound art |
| Instruction and skill integrity | Drift check after the run. Rollback of change C removes only a skill this pilot created | Deleting a shared company skill that already existed |

| Gate | State (2026-11-23) | Effect on the pilot |
|---|---|---|
| SEC-01 (critical): leading-wildcard allow rules (`Bash(*paperclip-issue-update.sh*)`, `Bash(*paperclip-upload-artifact.sh*)`), the `git push origin SOU-*` refspec, `git diff*`, the auto-memory write exemption; read-only `Bash(cat *)` redirect writes (expected to be denied in `-p` default mode; untested) | Open; 35-run lab test plan ready, not approved | **Conflict:** the wildcard rules are still in game-artist's allow list, so the pilot runs with the known gap. Changes A-C neither widen nor fix it. The catalog marks the rule "SEC-01: leading-wildcard allow rule, open security item" |
| SEC-02 remaining | Done: `requireBoardApprovalForNewAgents=true` and `canCreateAgents=false` live. Open: an agent may be able to self-PATCH `dangerouslySkipPermissions`, and so its own `extraArgs` (`UNVERIFIED`; test T-S needs its own approval); `agents.json` still declares `canCreateAgents: true` for director, producer and project-manager | **Conflict:** if that self-PATCH works under `local_trusted`, game-artist could drop `--settings` from its own `extraArgs`, so change B is a configuration, not enforcement. The drift check reports it after the fact. **Conflict:** game-artist has `canCreateSkills=true` live while `agents.json` declares none; it could create or edit company skills during the skill pilot. Setting it to `false` first needs its own approval (KD-BD-8) |
| Auth Phase B, WS-2 and WS-5 | Isolated runs pending scheduling | No dependency for A-C; P1-P4 must not overlap a WS run |
| Phase D (`authenticated` mode) | Not started; the real fix for `local_trusted` | Until then, every config change in this pilot can be reverted by any local process, including agents |
| Option C (Cursor) / Cursor Batch B | Both Cursor agents paused (security gate KD-BD-4); spike plan G0-G8 not approved | Out of scope; the catalog marks every Cursor allow rule "not enforced (Cursor sandbox disabled)" |

U-B stays pending; U-F and K5 stay deferred (not touched here).

## Related documents
- [ADR-024](../decisions/ADR-024-knowledge-delivery-generated-role-packages.md), [ADR-019](../decisions/ADR-019-knowledge-tree-and-departments.md)
- [company-bootstrap.md](company-bootstrap.md) (role sync, OQ-040)
- [security-operations.md](security-operations.md)
- [open-questions.md](../roadmap/open-questions.md) (OQ-050)

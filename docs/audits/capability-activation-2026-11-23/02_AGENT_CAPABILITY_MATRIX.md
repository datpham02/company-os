# 2. Agent × Skills × Tools × Knowledge Matrix

Source: `config/paperclip/agents.json`, generated catalog views, skill roots, KD docs.  
Heartbeat note: several roles have `runtime.heartbeat.enabled: false`. Paperclip API was down during audit → live INVOKED/EFFECTIVELY USED for company Agents is **not re-verified live**; cited from catalog/SOU history where marked.

Ladder cells use: R / I / D / A / V / E (highest confirmed). `usedBy` alone ≠ V/E.

| Agent | Adapter / profile | Model | Skills should use | Skills can discover | Knowledge readable | Tools / permissions | Approved deps relevant | Usage evidence | Missing / conflicts |
|---|---|---|---|---|---|---|---|---|---|
| director | claude_local / read-only | claude-fable-5-1 | paperclip reporting; company policies | user Claude skills + company paperclip if cwd company-os | company knowledge if in workspace; **KD package not for director art skill** | read + issue-update; canCreateAgents/Skills declared | paperclip, claude-code, gh | Board Operator path via skill | No task→skill router; heartbeat? |
| producer | claude_local / read-only | sonnet-5-5 | paperclip; project registry | same class | company + project READMEs | read-only profile | paperclip, claude-code | historical SOU coordination | openspec candidate unused |
| project-manager | claude_local / read-only | sonnet-5-5 | paperclip; workflows | same | workflows/standards | read-only | paperclip, claude-code, openspec(R) | SOU PM tasks | openspec not installed |
| game-designer | claude_local / workspace-write | fable-5-1 | design standards; openspec (intended) | Claude skills in env; **not** cloned candidate packs | game design knowledge | workspace-write + Godot allow | claude-code, openspec(R), awesome-gamedev(R) | design docs tasks | openspec MISSING; candidate packs absent |
| ui-designer | claude_local / workspace-write | sonnet-5-5 | ui-ux-pro-max; google-design-md; design.md | ui-ux-pro-max **installed**; design candidates mostly **not** | UI knowledge; design.md if path works | search.py + design.md + Godot | ui-ux-pro-max(E path), google-design-md, candidates | allow rule present | many design candidates uninstalled; overlap with web skills |
| qa-engineer | claude_local / workspace-write | sonnet-5-5 | QA workflows; playwright (intended) | no playwright in ~/.claude.json now | QA knowledge | docker compose + Godot | playwright(R drift), docker conflict, gh | Godot QA runner allow | playwright config drift; docker ADR conflict |
| gameplay-programmer | **cursor** / workspace-write | gpt-5.3-codex-high | game code skills; REA on demand; awesome-gamedev | Cursor skills (~29 user); **Cursor paused** | project repo + company-os if opened | Cursor sandbox **disabled** (catalog) | cursor-cli, rea, gh; candidates | paused — no live Agent loop | KD Option C not approved; no allowlist enforcement |
| game-artist | claude_local / workspace-write | sonnet-5-5 | studio-art-identity-and-refinement; art workflows | skill in knowledge tree; **KD P1–P4 not approved** → not assumed assigned | art knowledge; **SOU-88 refused Company OS docs outside workspace** | comfy-draft/edit, art-ops, pixelfx, Godot, gh | comfy stack, birefnet, pixelfx | SOU-66/68/71/64/81 tool runs (catalog); heartbeat **off**; OQ-045 historically not live | pixelfx never in SOU agent logs; KD undelivered; Klein R&D not permitted |
| web-engineer | **cursor** / workspace-write | gpt-5.3-codex-high | web stack; design/motion candidates | Cursor skills; paused | web dept knowledge | Cursor (unenforced) | cursor-cli, gh; web candidates R-only | paused | same Cursor gate |
| code-reviewer | claude-reviewer-strict | (profile) | review rules | Claude | standards | strict reviewer profile | claude-code | review PRs when live | heartbeat off |

## Skill discovery reality

| Root | Count (approx) | Who sees it |
|---|---|---|
| `company-os/.claude/skills` | 1 (paperclip) | Claude in company-os |
| `knowledge/.../studio-art-identity-and-refinement` | 1 | Only if KD/skill sync assigns it |
| `~/.claude/skills` | ui-ux-pro-max + REA + synced pack | Claude Code user / adapters on that machine |
| `~/.cursor/skills-cursor` | ~29 | Cursor IDE / cursor-agent — **not** mapped into Claude roles |

**No Agent profile lists an explicit `desiredSkills` / skill router in agents.json.** Discovery is ambient (Claude/Cursor skill dirs) + role AGENTS.md text + (future) KD sync.

## Knowledge delivery state

| Artifact | Exists | Delivered to live Agent? |
|---|---|---|
| `generated/game-artist/*` | YES | **NO** — P1–P4 not approved |
| `generated/catalog/views/*.md` | YES (all roles) | Catalog is documentation; not runtime load |
| Role AGENTS.md under knowledge/ | YES | Sync/drift path; live drift noted in KD doc (`canCreateSkills`) |

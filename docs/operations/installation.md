# Installation

Order matters. Each step lists its verification. Commands are labelled `VERIFIED` (from the tool's official docs or tested on the machine) or `PLANNED` (depends on Game Studio code that does not exist).

## 1. Claude Code CLI

Already installed (2.1.316 at `~/.local/bin/claude` on the Windows studio machine). For new machines follow the official instructions at https://code.claude.com/docs.

Verify (`VERIFIED`):
```bash
claude --version
claude -p "Respond with hello."      # confirms login works; same probe Paperclip uses
```

## 2. Codex CLI

The standalone CLI is not installed; only app-bundled binaries exist (OQ-009). Install it per the official README at https://github.com/openai/codex. The README documents installation with npm. Check the README before running:

```bash
npm install -g @openai/codex       # per official README; package verified on npm (0.166.0)
codex --version
codex login                         # or: printenv OPENAI_API_KEY | codex login --with-api-key
codex login status
```

`codex login`, `--with-api-key`, and `login status` are `VERIFIED` in the CLI help.

## 3. Paperclip

`VERIFIED` from Paperclip's quickstart:

First-time setup used `npx paperclipai onboard --yes` (`local_trusted`, loopback; OQ-024). **Day to day, run the globally installed, pinned version, not `npx`.** `npx` wraps the server in npm, and its `npm_*` variables leak into every agent run (OQ-034):

```bash
npm install -g paperclipai@2026.1023.0   # once, and again only after an approved upgrade (OQ-008)
cd ~/game-studio-workspace              # never start it inside a repository
paperclipai run
```

- UI and API default to `http://localhost:3100` (API at `/api`).
- Use `paperclipai configure` to change settings later.
- On Windows npm blocks some install scripts of the global package (`@embedded-postgres/windows-x64` and others). Paperclip 2026.1023.0 still starts and uses its embedded PostgreSQL without them (verified 2026-11-04).
- Pin the version and record it in [../../dependencies/registry.yaml](../../dependencies/registry.yaml) (OQ-008).
- Do **not** clone Paperclip into this repository (ADR-002).

## 4. OpenSpec (optional; candidate dependency)

Installed (1.11.0). Upgrade only after approval (`VERIFIED` command, OpenSpec README):
```bash
npm install -g @fission-ai/openspec@latest
openspec --version
```

## 5. MCP servers (optional; candidate dependencies)

Currently registered in Claude Code (`claude mcp list`, 2026-11-03): `playwright` (`npx -y @playwright/mcp@latest --headless --isolated`) and `hoppscotch` (`npx -y @hoppscotch/mcp-server`). For Codex, Playwright MCP documents `codex mcp add playwright npx "@playwright/mcp@latest"`. Install/keep only after the dependency is approved.

### PixelFX (optional; integrated for `game-artist`)

Installed by the Board on 2026-11-21 at the reviewed commit, outside every agent workspace. No `npm install`; the export tools use only Node:
```bash
git clone https://github.com/patch-gg/pixelfx "$HOME/tools/pixelfx"
git -C "$HOME/tools/pixelfx" checkout 5294518
node "$HOME/tools/pixelfx/tools/render.mjs" ice/frost-nova --sheet --out <scratch folder>
```
`game-artist` may run only `list.mjs` and `render.mjs` from that folder ([dependencies/registry.yaml](../../dependencies/registry.yaml) `pixelfx`). Upgrading means a new review and a new commit in all three places.

### REA (optional; approved for `gameplay-programmer`, `PLANNED`, not installed)

Approved by the Board on 2026-11-21 with conditions ([registry](../../dependencies/registry.yaml) `rea`). Do not install for agents until OQ-046 (which Cursor MCP config) is answered. The Board runs, in a terminal with no secrets exported:
```bash
npm install -g rea-agents@6.10.1 --omit=optional        # pinned; skips Frida and its install script
rea --version                                            # expect 6.10.1
rea setup --client <client> --no-skill --tool-families direct,artifact,managed,native --dry-run --json
# read the plan: only one MCP entry, no skill, no Hopper, the four tool families; then:
rea setup --client <client> --no-skill --tool-families direct,artifact,managed,native --yes
```
`<client>` follows the OQ-046 answer. Never use interactive setup (it pre-selects a Hopper install), `--all-detected`, `--install-hopper`, the HTTP MCP transport, or `rea update`. Afterwards check that the client's MCP entry runs the global 6.10.1 install and sets `REA_MCP_TOOL_FAMILIES`, record the date here, and set the registry entry to `integrated`. Upgrading means a new review of the diff.

The Board's own Claude Code already has an older REA MCP entry (`npx -y rea-agents@6.7.0 mcp`) and the `reverse-engineer-anything` skill at user scope. They are the Board's personal tools, not this approval; agents' runs do not list that MCP server.

## 6. Studio setup in Paperclip

Import the company and agents instead of creating them in the UI: [company-bootstrap.md](company-bootstrap.md). The manual route below remains for reference. Follow [../integrations/paperclip-integration.md §9](../integrations/paperclip-integration.md#9-setup-procedure-summary):
1. Create the company from [../../knowledge/company/COMPANY.md](../../knowledge/company/COMPANY.md).
2. Create agents from [../../knowledge/company/ORGANIZATION.md](../../knowledge/company/ORGANIZATION.md) via [../../knowledge/company/workflows/agent-onboarding.md](../../knowledge/company/workflows/agent-onboarding.md).
3. Add the GitHub token as a company secret named `GITHUB_TOKEN`/`GH_TOKEN`/`PAPERCLIP_GITHUB_TOKEN` (`VERIFIED` names) and bind it to code-writing agents.

Optional, `UNVERIFIED` (OQ-007): preview a company import without writing:
```bash
npx paperclipai company import --help   # read the flags first; documented preview mode exists
```

## 7. Agent Runtime

`PLANNED`. Nothing to install. Do not attempt.

## 8. Verification checklist

- [ ] `node --version` ≥ 24.11
- [ ] `claude --version`, and `claude -p` probe works
- [ ] `codex --version` from the standalone install, and `codex login status` OK
- [ ] Paperclip UI reachable at `http://localhost:3100`
- [ ] Each Agent Instance passes Paperclip "Test Environment"
- [ ] `gh auth status` OK

## Related documents
[windows-setup.md](windows-setup.md) · [configuration.md](configuration.md) · [troubleshooting.md](troubleshooting.md)

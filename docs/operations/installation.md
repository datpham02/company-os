# Installation

Order matters. Each step lists its verification. Commands are labelled `VERIFIED` (from the tool's official docs or tested on the machine) or `PLANNED` (depends on Game Studio code that does not exist).

## 1. Claude Code CLI

Already installed (2.1.273 at `~/.local/bin/claude`). For new machines follow the official instructions at https://code.claude.com/docs.

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

```bash
npx paperclipai onboard --yes       # first-time setup; choose local_trusted when asked (OQ-024)
npx paperclipai run                 # start later
```

- UI and API default to `http://localhost:3100` (API at `/api`).
- Use `npx paperclipai configure` to change settings later.
- Pin the version for reproducibility: `npx paperclipai@<version> …` and record it in [../../dependencies/registry.yaml](../../dependencies/registry.yaml) (OQ-008).
- Do **not** clone Paperclip into this repository (ADR-002).

## 4. OpenSpec (optional; candidate dependency)

Installed (1.11.0). Upgrade only after approval (`VERIFIED` command, OpenSpec README):
```bash
npm install -g @fission-ai/openspec@latest
openspec --version
```

## 5. MCP servers (optional; candidate dependencies)

Currently registered in Claude Code (`claude mcp list`, 2026-11-03): `playwright` (`npx -y @playwright/mcp@latest --headless --isolated`) and `hoppscotch` (`npx -y @hoppscotch/mcp-server`). For Codex, Playwright MCP documents `codex mcp add playwright npx "@playwright/mcp@latest"`. Install/keep only after the dependency is approved.

## 6. Studio setup in Paperclip

Manual in v1 (UI). Follow [../integrations/paperclip-integration.md §9](../integrations/paperclip-integration.md#9-setup-procedure-summary):
1. Create the company from [../../company/COMPANY.md](../../company/COMPANY.md).
2. Create agents from [../../company/ORGANIZATION.md](../../company/ORGANIZATION.md) via [../../workflows/agent-onboarding.md](../../workflows/agent-onboarding.md).
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
[ubuntu-setup.md](ubuntu-setup.md) · [configuration.md](configuration.md) · [troubleshooting.md](troubleshooting.md)

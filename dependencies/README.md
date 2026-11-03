# Dependencies

External tools the studio uses or is evaluating. The data is in [registry.yaml](registry.yaml). The rules are in [../docs/design/dependency-system.md](../docs/design/dependency-system.md), and the process for adding one is [../workflows/add-external-dependency.md](../workflows/add-external-dependency.md).

**Nothing in this directory is vendored code** ([ADR-007](../docs/decisions/ADR-007-external-dependency-registry.md)).

| ID | Category | Status | License |
|---|---|---|---|
| `paperclip` | orchestration | approved (not installed) | MIT |
| `claude-code` | execution-provider | approved | proprietary |
| `codex` | execution-provider | approved (standalone not installed) | Apache-2.0 |
| `github-cli` | development-tools | integrated | MIT |
| `openspec` | specification | candidate | MIT |
| `claude-code-game-studios` | game-development | candidate | MIT |
| `awesome-gamedev-agent-skills` | game-development | candidate | Apache-2.0 |
| `playwright-mcp` | development-tools | candidate | Apache-2.0 |
| `hoppscotch-mcp` | development-tools | candidate | unknown |

Keep this table in sync with `registry.yaml` (a `PLANNED` script will generate it).

Category subdirectories (`game-development/`, `specification/`, `orchestration/`, `development-tools/`, `execution-provider/`) are created only when an entry needs long-form notes beyond its `notes` field.

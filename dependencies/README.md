# Dependencies

External tools the studio uses or is evaluating. The data is in [registry.yaml](registry.yaml). The rules are in [../docs/design/dependency-system.md](../docs/design/dependency-system.md), and the process for adding one is [../knowledge/company/workflows/add-external-dependency.md](../knowledge/company/workflows/add-external-dependency.md).

**Nothing in this directory is vendored code** ([ADR-007](../docs/decisions/ADR-007-external-dependency-registry.md)).

| ID | Category | Status | License |
|---|---|---|---|
| `paperclip` | orchestration | approved (not installed) | MIT |
| `claude-code` | execution-provider | approved | proprietary (Anthropic terms) |
| `codex` | execution-provider | approved (standalone not installed) | Apache-2.0 |
| `cursor-cli` | execution-provider | approved | proprietary (Cursor terms) |
| `openspec` | specification | candidate | MIT |
| `claude-code-game-studios` | game-development | candidate | MIT |
| `awesome-gamedev-agent-skills` | game-development | candidate | Apache-2.0 |
| `pixelfx` | game-development | integrated | MIT |
| `playwright-mcp` | development-tools | candidate | Apache-2.0 |
| `hoppscotch-mcp` | development-tools | candidate | unknown |
| `rea` | development-tools | evaluating | MIT |
| `docker-desktop` | development-tools | approved | Docker Subscription Service Agreement |
| `github-cli` | development-tools | integrated | MIT |
| `ui-ux-pro-max-skill` | web-design | integrated | MIT |
| `awesome-design-md` | web-design | candidate | MIT |
| `open-design` | web-design | candidate | Apache-2.0 |
| `taste-skill` | web-design | candidate | MIT |
| `impeccable` | web-design | rejected | Apache-2.0 |
| `react-bits` | web-design | candidate | MIT with Commons Clause |
| `emil-design-eng-skills` | web-design | candidate | MIT |
| `hallmark` | web-design | candidate | MIT |
| `google-design-md` | web-design | integrated | Apache-2.0 |
| `gsap-skills` | web-design | candidate | MIT |
| `scroll-world` | web-design | candidate | MIT |
| `canvas-ui` | web-design | candidate | MIT with Commons Clause |

Keep this table in sync with `registry.yaml` (a `PLANNED` script will generate it).

Category subdirectories (`game-development/`, `specification/`, `orchestration/`, `development-tools/`, `execution-provider/`) are created only when an entry needs long-form notes beyond its `notes` field.

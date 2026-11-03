# Dependency System

**Contract owner for:** how external tools are recorded, evaluated, installed, versioned, and retired. The data lives in [../../dependencies/registry.yaml](../../dependencies/registry.yaml).

## 1. Principles (ADR-007)

- Register, never vendor. No external source code in this repository.
- A registry entry is a *record*, not an approval. `integrationStatus` says how far adoption has gone.
- Every claim in an entry needs a source URL.

## 2. Entry fields

| Field | Required | Description |
|---|---|---|
| `id` | Yes | kebab-case identifier |
| `name` | Yes | Official name |
| `category` | Yes | §3 |
| `source.repository` | Yes* | Official repository URL (*or `source.docs` if closed source) |
| `source.docs` | No | Official documentation URL |
| `source.package` | No | Package name and registry, e.g. `npm:@fission-ai/openspec` |
| `license` | Yes | SPDX identifier or `unknown` |
| `required` | Yes | `true` if the studio cannot operate without it |
| `versionConstraint` | Yes | Semver range or `pinned:<version>` |
| `verifiedVersion` | No | Version actually tested, with date |
| `install.reference` | Yes | Link to official install instructions |
| `install.strategy` | Yes | §4 |
| `integrationStatus` | Yes | §5 |
| `usedBy` | No | Agent IDs or `studio` |
| `compatibility` | No | Notes: OS, Node version, providers |
| `notes` | No | Free text |

## 3. Categories

| Category | Meaning | Examples |
|---|---|---|
| `orchestration` | Runs or coordinates the studio | Paperclip |
| `execution-provider` | AI coding CLI | Claude Code, Codex |
| `specification` | Spec-driven development tools | OpenSpec |
| `game-development` | Game-dev agents, skills, templates | Awesome Gamedev Agent Skills, Claude Code Game Studios |
| `development-tools` | MCP servers and CLIs used during work | Playwright MCP, Hoppscotch MCP, GitHub CLI |

`execution-provider` is an addition to the four directories in the target structure. Providers are neither game-development nor generic development tools, and ADR-008 treats them specially.

## 4. Installation strategies

| Strategy | Meaning | Where installed |
|---|---|---|
| `global-cli` | Installed once on the machine (npm global, official installer, package manager) | User environment |
| `mcp-server` | Registered with a Provider's MCP config (`claude mcp add …`, `codex mcp add …`); usually run via `npx` | Provider config |
| `skill-pack` | Skills installed into a Provider's skills directory or as a Claude Code plugin | Provider config or Game Repository |
| `project-local` | Installed or initialized inside a Game Repository (e.g. `openspec init`) | Game Repository |
| `external-service` | Runs as its own application | Its own install (e.g. Paperclip) |
| `reference-only` | Studied for ideas; not installed | — |

## 5. Integration status

`candidate` → `evaluating` → `approved` → `integrated` → `deprecated` (or `rejected` from any earlier state).

| Status | Meaning |
|---|---|
| `candidate` | Listed; nobody has evaluated it |
| `evaluating` | An evaluation Task is open |
| `approved` | Board approved installation |
| `integrated` | Installed, configured, and documented in operations docs |
| `deprecated` | Being removed; `notes` names the replacement |
| `rejected` | Evaluated and declined; reason in `notes` |

## 6. Version management and updates

- `versionConstraint` is the policy; `verifiedVersion` is the fact.
- `external-service` and `execution-provider` dependencies SHOULD be pinned (they change behaviour often).
- Update policy: an upgrade is a Task. Read the upstream changelog → test on a scratch project → update `verifiedVersion` → Board approval for `required` dependencies.
- Validation (`PLANNED` script `scripts/check-dependencies`): compare installed versions (`<tool> --version`) against constraints and report drift.

## 7. Compatibility

Record OS (Ubuntu 24.04), Node.js version requirements, and which Providers a skill pack or MCP server supports. Known cross-dependency constraints: Paperclip requires Node.js 24.11+ (`VERIFIED`, Paperclip architecture docs); OpenSpec npm install requires Node.js 22.12.0+ (`VERIFIED`, OpenSpec README).

## 8. License tracking

- Record the SPDX license. `unknown` blocks approval.
- Copyleft licenses (GPL, AGPL) for anything copied into a Game Repository require Board approval.
- Apache-2.0 dependencies with a `NOTICE` file require keeping the notice if any file is redistributed.

## 9. External source references

- Use official repositories and documentation only. Aggregator sites are not sources.
- Where a dependency's own docs differ from third-party descriptions (counts of agents/skills, star counts), trust the dependency's repository at a recorded commit.

## Related documents
- [../../dependencies/registry.yaml](../../dependencies/registry.yaml) · [../../workflows/add-external-dependency.md](../../workflows/add-external-dependency.md) · [../decisions/ADR-007-external-dependency-registry.md](../decisions/ADR-007-external-dependency-registry.md)

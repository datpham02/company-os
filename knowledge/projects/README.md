# Projects

A project is a product. It belongs to one department and may have contributing departments. Its code and its own documents live in its own repository ([ADR-005](../../docs/decisions/ADR-005-independent-game-repositories.md)); this folder holds only the registry and one entrypoint per project.

| Project | Department | Type | Entrypoint |
|---|---|---|---|
| Lamplight Vigil | Game | game | [lamplight-vigil/README.md](lamplight-vigil/README.md) |
| Soucean Game | Web | platform | [soucean-game/README.md](soucean-game/README.md) |
| Deckbound | Game | game | [deckbound/README.md](deckbound/README.md) |

- [registry.yaml](registry.yaml): machine-readable registry. Schema: [project-config.schema.yaml](project-config.schema.yaml).
- Contract: [project-system.md](../../docs/design/project-system.md).
- New projects: [project-initialization.md](../company/workflows/project-initialization.md); existing repositories: [register-existing-repository.md](../company/workflows/register-existing-repository.md).

# Repository Terrain (web 3D visualization)

## When to use

Adding or changing the Repository Terrain view, its DTO layer, or `/v3/ops/terrain` API.

## Architecture

| Layer | Location |
|-------|----------|
| DTO + assembly | `src/metagit/core/web/terrain_service.py` |
| HTTP route | `GET /v3/ops/terrain` in `OpsWebHandler` |
| SPA page | `web/src/pages/TerrainPage.tsx` |
| Three.js scene | `web/src/components/terrain/terrainScene.ts` |
| API client types | `web/src/api/client.ts` (`getRepositoryTerrain`) |

## Data sources (no direct git from frontend)

- Workspace index rows (`WorkspaceIndexService`)
- Git inspect (`inspect_repo_state`, local commit windows via GitPython)
- CI status (`PipelineStatusService`, optional via `include_pipelines=false` for speed)
- Dependency arcs (`WorkspaceGraphService`, repo-to-repo edges only)
- Agent hints (filesystem: `AGENTS.md`, `llms.txt`, `docs/`)

## Adding a new visual signal

1. Extend pydantic models in `terrain_service.py` (`RepositoryTerrainNode` or nested DTO).
2. Populate in `RepositoryTerrainService._build_node` or helper.
3. Mirror types in `web/src/api/client.ts`.
4. Map to instanced mesh colors/geometry in `terrainScene.ts`.
5. Expose in `TerrainDetailPanel` when user-inspectable.
6. Add unit test in `tests/core/web/test_terrain_service.py`.

## Performance notes

- Use `THREE.InstancedMesh` for tiles, borders, beacons, agent markers.
- Avoid per-repo unique geometries; rebuild meshes on layer toggle (acceptable for v1).
- Default `limit=2000`; raise only when needed.
- **Code splitting:** route-level `React.lazy` for `TerrainPage`; dynamic `import('./terrainScene')` inside `RepositoryTerrainCanvas`; Vite `manualChunks` for `three-vendor` and `terrain-scene`.
- **Working-tree shaders:** `terrainTileMaterial.ts` injects instanced `aFracture` / `aFissure` / `aCrack` attributes into `MeshStandardMaterial` (vertex displacement + emissive fissures/conflicts).

## Verify

- `uv run pytest tests/core/web/test_terrain_service.py`
- `cd web && npm run build`
- Manual: `metagit web serve --open` → **Repository Terrain**

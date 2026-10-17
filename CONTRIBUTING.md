# Contributing to Trove

## Branching & merging

- Branch off `main` for every change (`feat/…`, `fix/…`, `ci/…`, `docs/…`).
- Open a PR into `main`. CI (lint, tests, smoke, chart lint) must pass.
- PRs are **squash-merged**; the **PR title becomes the commit subject** on
  `main`, and the merged branch is deleted automatically.

## Conventional Commits

The **PR title must follow [Conventional Commits](https://www.conventionalcommits.org/)**,
because it becomes the squash commit that drives automated semantic versioning
on merge to `main`. A CI check (`PR Title`) enforces this.

```
<type>[optional scope][!]: <description>
```

**Types** and their effect on the next release version:

| Type | Example | Version bump |
|------|---------|--------------|
| `feat` | `feat: let candidates archive jobs` | **minor** (x.**Y**.0) |
| `fix` | `fix: keep fit score when editing a job` | **patch** (x.y.**Z**) |
| `feat!` / `fix!` / any `!` | `feat!: require API keys for the REST API` | **major** (**X**.0.0) |
| `docs`, `chore`, `ci`, `build`, `refactor`, `perf`, `test`, `style`, `revert` | `docs: document MCP setup` | patch (default) |

A breaking change can also be signalled with a `BREAKING CHANGE:` footer in the
PR body.

### Guidelines
- Keep the subject imperative and lowercase, no trailing period
  (e.g. `fix: handle empty resume`, not `Fixed the bug.`).
- Use a scope when it helps: `feat(mcp): …`, `fix(ui): …`.

## API changes

The REST API and the MCP tools share one service layer, and every MCP tool must
have a REST operation with the same `operationId` (a test enforces this). After
changing either, regenerate the published contract and commit it:

```bash
make openapi    # writes docs/openapi.json and docs/mcp-tools.json
```

CI fails if `docs/` is stale.

## Database changes

Add a migration under `backend/app/migrations/versions/`, chained via
`down_revision`. CI runs `alembic upgrade head && alembic check` against Postgres,
so a model change without a matching migration fails the build.

## Releases

On merge to `main`, CI computes the next `vX.Y.Z` from the PR title, tags it,
creates a GitHub release (with the OpenAPI spec and MCP tool definitions
attached), builds/signs/attests the container images (`latest`, `X.Y.Z`, `X.Y`,
`sha-<short>`) and publishes the Helm chart. See the README's **CI / releases**
section.

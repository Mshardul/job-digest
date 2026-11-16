# Instructions for coding agents

This file is read by AI coding agents (Claude Code via `CLAUDE.md`, Cursor, and others) working on Job Digest.

## Sources of truth

- **What to build:** [docs/SPEC.md](docs/SPEC.md)
- **How it is structured:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Privacy guards:** [docs/SECURITY.md](docs/SECURITY.md)
- **What to build next:** [docs/PLAN.md](docs/PLAN.md)

Read the relevant sections before writing code. If code and spec disagree, the spec wins.

## Rules

1. **Work from the spec.** Do not add features, sources, settings or dependencies the spec does not call for.
2. **Ask before deviating.** If the spec is unclear, wrong, or impossible to follow, stop and ask the owner. Do not guess and do not silently work around it. Once a change is agreed, update the spec in the same pull request.
3. **One pull request per milestone.** Keep each PR to the scope of its milestone in PLAN.md, and describe in the PR what the owner should review.
4. **No live API calls in tests.** Tests use recorded fixtures under `tests/fixtures/`. Trial calls against real APIs (for example the AND/OR checks) are done manually and their findings written into the PR.
5. **Never commit private data.** No `.env`, `profile.yaml`, database files, real job listings, or real email addresses. Fixtures are sanitized. Example files use neutral sample values, never the owner's profile.
6. **Never log content.** Logs carry counts only. All logging goes through the masking filter. Commands that print job content must refuse to run in GitHub Actions.
7. **Keep it free.** No dependency or service that needs payment.
8. **Keep ports clean.** The pipeline depends only on the `Source`, `Storage`, `Notifier` and `Renderer` protocols. Database code stays portable: no dialect-specific SQL; schema changes go through Alembic migrations.
9. **Store UTC.** Convert to the profile's timezone only when rendering.

## Before opening a pull request

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
uv run pre-commit run --all-files
```

All must pass.

## Conventions

- Python 3.12, type hints everywhere, mypy clean.
- pydantic models for configuration and normalized jobs.
- httpx for HTTP, feedparser for RSS.
- Tests mirror the source layout under `tests/unit/`; database and libSQL tests live under `tests/integration/`.

# Job Digest — Architecture

How Job Digest is structured, configured and deployed. What it does is defined in [SPEC.md](SPEC.md); privacy guards are in [SECURITY.md](SECURITY.md).

---

## 1. Principles

- **Free to run.** Every component fits a free tier: GitHub Actions, Turso, Gmail SMTP.
- **Nothing personal in the repository.** No credentials, no job listings, no preferences. The repository is public; each person runs their own fork with their own secrets.
- **Swappable edges.** Sources, storage, notifiers and renderers sit behind small interfaces, so a fork can replace one without touching the pipeline.
- **The repository ships what the owner uses.** Other adapters are documented, not bundled.

## 2. Deployment model

```
Public repo (code only)
   │ fork
   ▼
Your fork ──► GitHub Actions (daily cron) ──► job boards (public APIs/RSS)
                    │                    ├──► your database (Turso by default)
                    │                    └──► your SMTP account ──► your inbox
                    └── secrets: the checklist in the README (step 6), mirrored by §4 below
```

- Each fork runs fully separately: its own schedule, database, mail account and profile. No data is shared between forks.
- Workflow logs on a public repository are public, so the code never prints profile values, job lists or email addresses (see SECURITY.md).
- GitHub disables scheduled workflows on new forks, and on public repositories after 60 days without activity. The README covers enabling the workflow after forking, and a keepalive workflow keeps the schedule active without committing data. The exact keepalive mechanism is verified in milestone 8.
- The schedule is a cron line in `.github/workflows/digest.yml` (`15 2 * * *`, i.e. 7:45 AM IST). A fork changes the time by editing that one line.

## 3. Ports and adapters

The pipeline depends only on four interfaces, defined as Python `Protocol`s. Concrete adapters are registered in an in-repo registry and chosen by configuration.

| Port | Responsibility | Adapters in this repo |
|---|---|---|
| `Source` | Fetch raw listings and map them to the common job shape | `himalayas`, `jobicy`, `remoteok`, `wwr` |
| `Storage` | Persist jobs, evaluations, sent history and runs | `sqlalchemy` (SQLite locally, Turso in production) |
| `Notifier` | Deliver a rendered message to one recipient | `smtp` |
| `Renderer` | Turn a selection into an email body | `compact` |

### 3.1 Required environment variables

Each adapter declares the environment variables it needs. At startup the run checks them all and stops with a message naming any that are missing, before any work is done.

### 3.2 Adding an adapter

1. Implement the port's `Protocol` in a new module in the matching package (for example `src/job_digest/notifiers/telegram.py`).
2. Declare its required environment variables.
3. Register it in that package's `registry.py`.
4. Add tests with recorded fixtures; no live calls.
5. Select it through configuration.

Adapters used only by a fork stay in that fork.

## 4. Configuration

Configuration is split three ways by sensitivity.

| Kind | Contents | Where it lives | In the repository |
|---|---|---|---|
| **Credentials** | `DATABASE_URL`, `TURSO_AUTH_TOKEN`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `NOTIFY_TO`, `ALERT_TO` | GitHub Secrets; local `.env` | `.env.example` with placeholders |
| **Personal profile** | Skills and weights, aliases, role tiers, exclusions, primary languages, eligible regions, scoring weights (`scoring`), `skills_saturation`, `min_fit`, timezone, `profile_version` | `JOB_DIGEST_PROFILE` secret (YAML); local `profile.yaml` | `profile.example.yaml` with neutral sample values |
| **Settings** | Enabled sources and queries, page cap, recent-bucket days, retention days, `db.warmup_on_start`, `alerts.enabled` | Defaults in code | Yes; each overridable by environment variable |

Notes:

- The README's secrets checklist is the list of every secret a fork must set. When a credential is added here, it is added there, to `.env.example` and to the `env` block of `digest.yml` in the same pull request; a test checks the last two against each other (PLAN, milestone 8).
- The owner's real profile never appears in the repository, not even as the example. Docs and the spec describe how the profile works and use neutral sample values; anything private lives in the profile secret.
- A GitHub secret cannot be read back once saved, so keep a local copy of `profile.yaml`.
- `job-digest validate-profile` checks the profile locally, and runs as the first step of every workflow.
- Settings overrides use the `JOB_DIGEST_` prefix (for example `JOB_DIGEST_RECENT_DAYS`, `JOB_DIGEST_ALERTS_ENABLED`, `JOB_DIGEST_DB_WARMUP_ON_START`).

## 5. Storage

- **SQLAlchemy** for all database access, with portable column types (JSON for lists) and no dialect-specific SQL, so the same code runs on any SQLAlchemy-supported database.
- **Alembic** migrations are applied automatically at the start of every run. A failed migration stops the run and raises an alert.
- **`DATABASE_URL`** selects the database by its URL scheme.
- **Default production database: Turso** (SQLite-compatible, free plan with no time limit and no card). Local development and tests use a plain SQLite file. The SQLAlchemy driver for Turso is confirmed in milestone 1.
- **Tested combinations:** SQLite and Turso only (Turso through a local libSQL server in CI). Other databases, such as Postgres on Neon or Supabase, are supported in principle; a fork that uses one adds and runs its own tests.
- **Connection resilience:**
  - The first connection always retries a few times with short backoff.
  - `db.warmup_on_start` (off by default) additionally runs `SELECT 1` with retries before the pipeline starts, for providers with slow cold starts.
  - A database paused by its provider is not handled; it has to be resumed from the provider's dashboard. The daily run's own activity keeps free databases from pausing while the schedule is alive.

## 6. Email delivery

- **v1 notifier: generic SMTP.** Tested with Gmail: `smtp.gmail.com`, port 587 with STARTTLS, using a Google app password (requires 2-Step Verification). A simple setup sends from the owner's own address to the owner's own address.
- **First-run deliverability:** the first emails may land in spam; mark them "Not spam" once.
- Outlook (OAuth) and Resend are planned as further notifiers after v1.

## 7. Time

All timestamps are stored in UTC. Conversion to the profile's timezone happens only when rendering.

## 8. Tooling

| Concern | Tool |
|---|---|
| Language | Python 3.12 |
| Packaging and environments | uv |
| Lint and format | ruff |
| Types | mypy |
| Tests | pytest, with recorded HTTP fixtures |
| HTTP | httpx |
| RSS | feedparser |
| Models and config validation | pydantic |
| Database | SQLAlchemy, Alembic |
| Hooks | pre-commit |
| CI and scheduling | GitHub Actions |

## 9. Workflows

| Workflow | Trigger | Does |
|---|---|---|
| `ci.yml` | Push, pull request | ruff, mypy, pytest (SQLite + local libSQL), gitleaks over full history, zizmor, pip-audit |
| `codeql.yml` | Push, pull request, weekly | CodeQL analysis |
| `digest.yml` | Daily cron, manual dispatch | `validate-profile`, then `job-digest run` |
| `keepalive.yml` | Scheduled | Keeps `digest.yml` from being disabled for inactivity |

All workflows use minimal permissions and pin third-party Actions to commit SHAs. Pull requests from forks never receive secrets.

## 10. Releases

Releases are tagged, and `CHANGELOG.md` lists what changed in each, so fork owners know when and why to sync.

## 11. Repository layout

The full layout once v1 is built. The documentation and examples exist now; code, tests, workflows and tool configuration are added in the milestones of [PLAN.md](PLAN.md).

```
job-digest/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                  # lint, types, tests, gitleaks, zizmor, pip-audit
│   │   ├── codeql.yml              # CodeQL code scanning
│   │   ├── digest.yml              # daily run (cron) — edit the cron line to change the time
│   │   └── keepalive.yml           # keeps the daily schedule from being auto-disabled
│   └── dependabot.yml              # dependency and Actions updates
├── docs/
│   ├── SPEC.md                     # what Job Digest does (source of truth)
│   ├── ARCHITECTURE.md             # structure, configuration, deployment
│   ├── SECURITY.md                 # privacy and security guards
│   └── PLAN.md                     # build milestones and post-v1 backlog
├── migrations/                     # Alembic database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/                   # one file per schema change
├── scripts/
│   └── block_private_files.py      # pre-commit hook: rejects .env, profile.yaml, *.db, *.sqlite, *.sqlite3
├── src/
│   └── job_digest/
│       ├── __init__.py
│       ├── cli.py                  # run, dry-run, validate-profile, explain, funnel
│       ├── pipeline.py             # the daily pipeline, step by step
│       ├── alerts.py               # operator alerts (silent sources, DB, migrations)
│       ├── redaction.py            # log masking filter
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py         # code defaults, env overrides
│       │   ├── profile.py          # profile model and validation
│       │   └── env.py              # required-env-var checks per adapter
│       ├── models/
│       │   ├── __init__.py
│       │   └── job.py              # normalized job shape
│       ├── sources/                # Source port and adapters
│       │   ├── __init__.py
│       │   ├── base.py             # Source protocol
│       │   ├── registry.py
│       │   ├── http.py             # shared client: User-Agent, delay, backoff
│       │   ├── himalayas.py
│       │   ├── jobicy.py
│       │   ├── remoteok.py
│       │   └── wwr.py
│       ├── processing/
│       │   ├── __init__.py
│       │   ├── normalize.py        # title/company normalization, seniority
│       │   ├── dedupe.py           # same company + title; richest copy wins
│       │   ├── regions.py          # region parsing and eligibility
│       │   ├── gates.py            # hard filters with exclusion reasons
│       │   ├── scoring.py          # role, skills, completeness; score breakdown
│       │   └── selection.py        # recent bucket, min fit, top 10
│       ├── storage/                # Storage port and SQLAlchemy adapter
│       │   ├── __init__.py
│       │   ├── base.py             # Storage protocol
│       │   ├── tables.py           # jobs, job_evaluations, sent_history, runs
│       │   ├── sqlalchemy_store.py
│       │   ├── connection.py       # engine, retries, optional warm-up
│       │   └── retention.py        # strips old descriptions
│       ├── notifiers/              # Notifier port and adapters
│       │   ├── __init__.py
│       │   ├── base.py             # Notifier protocol
│       │   ├── registry.py
│       │   └── smtp.py
│       └── renderers/              # Renderer port and adapters
│           ├── __init__.py
│           ├── base.py             # Renderer protocol
│           ├── registry.py
│           └── compact.py          # the compact daily email
├── tests/
│   ├── conftest.py
│   ├── fixtures/                   # recorded, sanitized source responses
│   │   ├── himalayas/
│   │   ├── jobicy/
│   │   ├── remoteok/
│   │   ├── wwr/
│   │   └── skills/                 # known skill-matching false and true positives
│   ├── unit/                       # mirrors src/job_digest/
│   │   ├── config/
│   │   ├── processing/
│   │   ├── renderers/
│   │   ├── sources/
│   │   └── test_redaction.py       # fails if profile values leak into logs
│   └── integration/
│       ├── test_sqlite.py
│       └── test_libsql.py          # against a local libSQL server
├── .env.example                    # credential placeholders
├── .gitignore
├── .pre-commit-config.yaml
├── AGENTS.md                       # rules for AI coding agents
├── CHANGELOG.md
├── CLAUDE.md                       # points Claude Code to AGENTS.md
├── LICENSE                         # MIT
├── README.md
├── alembic.ini
├── profile.example.yaml            # sample profile with neutral values
├── pyproject.toml
└── uv.lock
```

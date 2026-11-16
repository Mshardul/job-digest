# Job Digest

Job Digest reads public remote-job boards every morning, filters out what you can't or wouldn't apply to, scores the rest against your skills, and emails you up to ten of the best new jobs, each linked straight to its apply page.

- **Remote only**, filtered to the regions you can work from.
- **Never repeats** a job it has already sent you.
- **Free to run**: GitHub Actions, a free Turso database and your own email account.
- **Private by design**: the repository holds code only. Your credentials, profile and job history live in your own secrets and database.

> **Status:** in development. The documents in `docs/` describe the target system; the code is built milestone by milestone as described in [docs/PLAN.md](docs/PLAN.md).

---

## How it works

```
Himalayas ┐
Jobicy    ├─► normalize ─► dedupe ─► gates ─► score ─► select top 10 ─► email
RemoteOK  │                                                      │
WWR       ┘                         every job stored ◄───────────┘
```

1. **Fetch** recent listings from Himalayas, Jobicy, RemoteOK and We Work Remotely (about nine requests a day).
2. **Normalize** them into one shape: title, company, regions, pay with period, seniority, apply link.
3. **Deduplicate**: the same company and title on two boards is one job.
4. **Gate**: drop jobs that aren't remote, aren't open to your regions, are the wrong role or level, are older than 30 days, are closed, or were already sent.
5. **Score** 0–100: role fit (40), skills fit (40) and completeness, meaning region known and pay listed (20). Jobs whose role-plus-skills fit is below your `min_fit` are dropped.
6. **Select** up to ten, newest week first, and email them.

Every fetched job is stored with its status and score, so you can always see why a job was or wasn't sent. Full details are in [docs/SPEC.md](docs/SPEC.md).

A digest entry looks like this:

```
Staff Backend Engineer — Acme · 72
Full-time · Staff · Worldwide · $150–180k/yr · 1d ago · via Himalayas
Python, Go, AWS
```

---

## Repository layout

```
job-digest/
├── docs/                   # SPEC, ARCHITECTURE, SECURITY, PLAN, HOWTO
├── src/job_digest/         # the application (sources, processing, storage, notifiers, renderers)
├── migrations/             # Alembic database migrations
├── tests/                  # unit and integration tests, recorded fixtures
├── scripts/                # pre-commit helpers
├── .github/                # workflows and Dependabot
├── .env.example            # credential placeholders
└── profile.example.yaml    # sample profile with neutral values
```

Only the documentation and examples exist yet; code, tests and workflows arrive milestone by milestone ([docs/PLAN.md](docs/PLAN.md)). The full file-by-file layout is in [docs/ARCHITECTURE.md §11](docs/ARCHITECTURE.md#11-repository-layout).

Files never committed (blocked by `.gitignore` and a pre-commit hook): `.env`, `profile.yaml`, `*.db`, `*.sqlite`, `*.sqlite3`.

---

## Run your own copy

Job Digest is meant to be forked: each person runs their own fork with their own credentials and profile. Nothing is shared between forks.

### 1. Fork and clone

Fork this repository on GitHub, then:

```bash
git clone https://github.com/<you>/job-digest.git
cd job-digest
uv sync
uv run pre-commit install
```

### 2. Create a database

Create a free [Turso](https://turso.tech) database and note its URL and an auth token. For local runs you can skip this and use a SQLite file.

### 3. Set up email

Job Digest sends through SMTP. With Gmail:

1. Turn on 2-Step Verification for your Google account.
2. Create an **app password** and use it as `SMTP_PASSWORD`.
3. Use `smtp.gmail.com`, port `587`.

Sending from your own address to your own address is the simplest setup.

### 4. Write your profile

```bash
cp profile.example.yaml profile.yaml
cp .env.example .env
```

Edit `profile.yaml` with your skills and weights, role tiers, exclusions, eligible regions and timezone, and `.env` with your credentials. Then check the profile:

```bash
uv run job-digest validate-profile
```

### 5. Try it locally

```bash
uv run job-digest dry-run
```

This fetches, scores and prints the email that would be sent, with scores, without sending anything. Use it, with `job-digest explain`, to tune your weights, `skills_saturation` and `min_fit`. `dry-run` only works locally; it refuses to run in GitHub Actions because Actions logs on a public fork are public.

### 6. Add GitHub secrets

In your fork: **Settings → Secrets and variables → Actions → New repository secret**.

**Secrets checklist.** Tick each one off; a missing required secret stops the run with a message naming it.

| ☐ | Secret | Required | Value |
|---|---|---|---|
| ☐ | `DATABASE_URL` | Yes | Your Turso database URL |
| ☐ | `TURSO_AUTH_TOKEN` | Yes (Turso) | Your Turso auth token |
| ☐ | `SMTP_HOST` | Yes | e.g. `smtp.gmail.com` |
| ☐ | `SMTP_PORT` | Yes | e.g. `587` |
| ☐ | `SMTP_USERNAME` | Yes | Your email address |
| ☐ | `SMTP_PASSWORD` | Yes | Your app password |
| ☐ | `NOTIFY_TO` | Yes | Where the digest goes |
| ☐ | `ALERT_TO` | No | Where operator alerts go (defaults to `NOTIFY_TO`) |
| ☐ | `JOB_DIGEST_PROFILE` | Yes | The full contents of your `profile.yaml` |

Every secret here must also appear in `.env.example` and in the `env` block of `.github/workflows/digest.yml`; a test checks that the last two match. A secret can't be viewed after it is saved, so keep your local `profile.yaml`. When you change it, update the secret and bump `profile_version`.

### 7. Turn on security features

In **Settings → Code security**, enable secret scanning with push protection, Dependabot, and private vulnerability reporting. In **Settings → Actions → General**, set workflow permissions to read-only. The same settings can be switched on with the GitHub CLI: see [docs/HOWTO.md](docs/HOWTO.md#repository-security-setup-github-settings). Background: [docs/SECURITY.md](docs/SECURITY.md).

### 8. Enable the workflows

GitHub disables scheduled workflows on forks. Open the **Actions** tab, enable workflows, then run **digest** once by hand (**Run workflow**) to check everything works.

The digest runs daily at **7:45 AM IST** (`15 2 * * *` in UTC). To change the time, edit the `cron` line in `.github/workflows/digest.yml`. GitHub may start scheduled runs a little late.

GitHub also disables schedules on public repositories after 60 days without activity; `keepalive.yml` prevents that.

### 9. First emails

The first digests may land in spam. Mark one as "Not spam" and later ones arrive in your inbox.

---

## Configuration

Configuration is split by sensitivity:

- **Credentials** (database, SMTP, addresses): GitHub Secrets, or `.env` locally.
- **Profile** (skills, weights, roles, exclusions, regions, minimum score): the `JOB_DIGEST_PROFILE` secret, or `profile.yaml` locally.
- **Settings** (sources and queries, page cap, recent-bucket days, retention, DB warm-up, alerts): defaults in code, each overridable by an environment variable.

Details: [docs/ARCHITECTURE.md §4](docs/ARCHITECTURE.md#4-configuration).

## Commands

| Command | What it does |
|---|---|
| `job-digest run` | Full daily pipeline |
| `job-digest dry-run` | Everything except sending; prints the email with scores (local only) |
| `job-digest validate-profile` | Checks your profile for errors |

## Using another database or notifier

Sources, storage, notifiers and renderers are adapters behind small interfaces. This repository ships the ones its owner uses: four job boards, SQLAlchemy storage (SQLite and Turso) and SMTP email.

- **Another database:** storage uses SQLAlchemy with portable types and no dialect-specific SQL, so pointing `DATABASE_URL` at, for example, Postgres should work. Only SQLite and Turso are tested here; add tests in your fork for anything else.
- **Another notifier, source or renderer:** implement the protocol in the matching package, declare its required environment variables, and register it. See [docs/ARCHITECTURE.md §3.2](docs/ARCHITECTURE.md#32-adding-an-adapter).

## Development

```bash
uv sync
uv run pre-commit install
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
uv run pre-commit run --all-files
```

Tests never call live APIs; they use recorded fixtures in `tests/fixtures/`. AI coding agents follow [AGENTS.md](AGENTS.md).

## Staying up to date

Releases are tagged and listed in [CHANGELOG.md](CHANGELOG.md). Sync your fork from GitHub's **Sync fork** button.

## Data sources

Listings come from [Himalayas](https://himalayas.app), [Jobicy](https://jobicy.com), [RemoteOK](https://remoteok.com) and [We Work Remotely](https://weworkremotely.com). Each job in the email credits its source and keeps a link to the original listing.

## License

[MIT](LICENSE)

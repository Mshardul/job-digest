# Job Digest — Implementation Plan

Job Digest is built by an AI coding agent working from [SPEC.md](SPEC.md) and [ARCHITECTURE.md](ARCHITECTURE.md). The owner reviews each milestone as one pull request. Each milestone below states what is built, what is verified, and what the owner reviews before merging.

## Order

```
1 Skeleton ─► 2 Himalayas end-to-end ─┬─► 3 Jobicy, RemoteOK, WWR ─┐
                                      └─► 4 Dedupe/closed ─► 5 Gates ┴─► 6 Scoring ─► 7 Email ─► 8 Automation
```

After milestone 2, milestone 3 can run alongside 4 and 5. After milestone 8, Job Digest runs for a few days for the owner alone before friends are added.

---

## Milestone 1 — Skeleton

**Done ahead of the milestone** (the repository is public, so the privacy guards came first): `.pre-commit-config.yaml` with gitleaks, private-key detection and the blocked-file hook (`scripts/block_private_files.py`); `ci.yml` with a full-history gitleaks scan and the pre-commit hooks. The rest of the guard list below stays in this milestone.

**Build**
- Repository layout as in the README, `pyproject.toml` managed by uv.
- ruff, mypy, pytest and pre-commit configured; `ci.yml` running all checks.
- Security guards from SECURITY.md: pre-commit hooks (gitleaks, private-key detector, blocked-file hook), CI scans (gitleaks full history, zizmor, pip-audit, CodeQL), Dependabot.
- Port `Protocol`s and registries for sources, storage, notifiers and renderers.
- Settings with code defaults and env overrides; profile model with validation; `job-digest validate-profile`.
- Startup check of each adapter's required environment variables.
- Log masking filter and the leak test.
- SQLAlchemy models (`jobs`, `job_evaluations`, `sent_history`, `runs`) with `user_id`; first Alembic migration; auto-migrate on start; connection retry and `db.warmup_on_start`.
- Confirm the Turso SQLAlchemy driver; CI runs storage tests against SQLite and a local libSQL server.
- `.env.example`, `profile.example.yaml` (neutral values).

**Review:** the schema, above all.

## Milestone 2 — Himalayas end-to-end

**Build**
- Himalayas source adapter with pagination rules, User-Agent, delay and 429 backoff.
- Normalization into the common job shape; recorded fixtures for tests.
- `job-digest run` storing fetched jobs and a `runs` row; a CLI command to inspect stored jobs locally.

**Verify by trial:** AND/OR meaning of multi-word `q`; behaviour of a `country` filter; whether the feed is complete (`complete_feed`, SPEC §5.5). Adjust queries in settings.

**Review:** real rows in a local database — are titles, pay, regions and dates parsed correctly?

## Milestone 3 — Jobicy, RemoteOK, WWR

**Build:** the three remaining source adapters, each with fixtures and tests.

**Verify by trial:** AND/OR meaning of RemoteOK multi-tag filters; which sources return a complete feed.

**Review:** per-source rows and counts.

## Milestone 4 — Dedupe, title normalization, closed detection

**Build**
- Title and company normalization.
- Cross-source dedupe (same normalized company + title), keeping the richest copy and filling `also_on`.
- Marking jobs absent from their source feed as `closed`, for sources with `complete_feed` only (SPEC §5.5).

**Review:** a sample of merged duplicates and closed jobs.

## Milestone 5 — Gates and region parsing

**Build**
- All gates from SPEC §6, each writing its `exclusion_reason`.
- Region parsing: structured fields first, then the description keyword pass; `eligible_regions` from the profile.

**Measure:** the share of jobs left with unknown regions (`–`).

**Review:** excluded jobs grouped by reason; spot-check wrongly dropped or wrongly kept jobs.

## Milestone 6 — Scoring, selection, profile versioning, dry-run

**Build**
- Scoring from SPEC §7: role fit, skills fit with saturation and location factors, completeness, language penalty.
- Skill-matching rules from SPEC §7.3 and the fixture set of known false and true positives.
- Score breakdown, region source and run funnel stored (SPEC §7.6, §10.5); `explain` and `funnel` commands (local only).
- Selection from SPEC §8: recent bucket, fallback to older jobs, `min_fit`, tie-break, top 10, no repeats.
- `profile_version` recorded with every score.
- `job-digest dry-run` printing the would-be email with scores (local only).

**Calibrate:** run dry-runs over several days of stored jobs and set `min_fit` and `skills_saturation`. Add every false positive found to the fixture set. This is the most important review of the build.

## Milestone 7 — Email

**Build**
- SMTP notifier (tested with Gmail and an app password).
- Compact renderer: thin-day note, empty-day email, source-failure footer.
- Operator alerts (`ALERT_TO`, falling back to `NOTIFY_TO`; on by default).

**Decide:** the exact email template (SPEC §9.3) — compare a few variants.

**Verify:** manual sends to the owner's own inbox; check spam placement.

## Milestone 8 — Automation

**Build**
- `digest.yml`: daily cron at 7:45 AM IST, `validate-profile` first, every secret from the README checklist wired in, minimal permissions. A test fails if a variable in `.env.example` is missing from the workflow's `env` block.
- Retention: strip descriptions after ~90 days.
- `keepalive.yml`, after verifying the current keepalive mechanism.
- Silent-source detection (zero jobs for 2–3 runs) feeding alerts.
- README setup steps checked end to end on a fresh fork.

**Verify:** GitHub's failed-workflow notifications reach the owner.

**Then:** run for a few days for the owner only, then add friends.

---

## Later (after v1)

- **Notifiers:** Resend (second adapter), Outlook via OAuth.
- **Channels:** WhatsApp, Telegram.
- **Sources:** company ATS boards (Greenhouse, Lever, Ashby).
- **Filtering:** timezone-overlap filtering using the stored `timezone_restriction`.
- **Pay:** pay-based scoring, with currency conversion.
- **Eligibility:** an LLM check for jobs whose regions are unknown.
- **Outreach:** a separate project (browser extension) that drafts cold emails for the job page being viewed. Not part of this repository.
- **Calibration:** a `label <job> good|bad` command to build a labelled set for tuning weights.
- **Liveness:** a pre-send check that the apply link still works, for the selected jobs only.
- **Profile tooling:** generate a profile from a personal facts file; a company-geography preference.
- **Users:** per-user profiles with a UI for editing skills, weights and roles; the configurable newsletter.
- Recheck source terms on redistribution before any public newsletter.

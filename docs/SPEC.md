# Job Digest — Product Specification

This document defines what Job Digest does. It is the source of truth for implementation: code follows this spec, and any deviation is agreed first and then written here.

Related documents:
- [ARCHITECTURE.md](ARCHITECTURE.md) — how the code is structured, configured and deployed
- [SECURITY.md](SECURITY.md) — privacy and security guards
- [PLAN.md](PLAN.md) — build milestones and the post-v1 backlog

---

## 1. Purpose

Job Digest fetches remote job listings from public job boards, filters them against a personal profile, scores what is left, and emails a short daily list of the best matches. Every job in the email links straight to its apply page.

The goal is a list short enough to read over coffee: at most ten jobs a day, never a job seen before, and nothing that the reader cannot actually apply to.

## 2. Scope

### 2.1 In scope for v1

- Remote jobs only, and only jobs open to the profile's eligible regions (or whose eligibility cannot be determined; see §6.2).
- One user: the repository owner. The data model carries a `user_id` from day one so more users can be added without a schema rewrite.
- Four public sources: Himalayas, Jobicy, RemoteOK and We Work Remotely (§4).
- One compact daily email, sent around 7:45 AM IST.
- Every fetched job is stored with its status and score, so past decisions can be inspected.
- Zero cost: every component runs on a free tier.

### 2.2 Out of scope for v1

- Scraping LinkedIn, Naukri, Indeed or any site that forbids it.
- Company career pages and ATS boards (Greenhouse, Lever, Ashby).
- LLM-based checks of any kind.
- Filtering by timezone overlap (the field is stored, not used).
- Pay-based scoring and currency conversion.
- A UI for editing the profile.
- Outreach help (finding contacts, drafting cold emails). Planned as a separate project; see PLAN.md.

These are tracked in the backlog in [PLAN.md](PLAN.md).

### 2.3 Audience over time

1. **v1:** the owner only.
2. **Next:** a few friends, each receiving their own separate email.
3. **Long term:** a configurable newsletter where each person sets their own domain, skills, roles and weights.

Until the newsletter exists, anyone else can run Job Digest by forking the repository and supplying their own credentials and profile (see the README).

## 3. Daily pipeline

Each run performs these steps in order:

1. **Validate** the profile and required environment variables; stop with a clear message if anything is missing or malformed.
2. **Migrate** the database to the latest schema (fails loudly on error).
3. **Fetch** listings from every enabled source (§4).
4. **Normalize** each listing into the common job shape (§5).
5. **Deduplicate** across sources (§5.4).
6. **Close jobs** that disappeared from sources that return a complete feed (§5.5).
7. **Gate**: apply hard filters; failures are stored as `excluded` with a reason (§6).
8. **Score** the remaining jobs from 0 to 100 and keep the score breakdown (§7).
9. **Select** up to ten jobs for the digest (§8).
10. **Render and send** the email (§9).
11. **Record** sent history, job statuses, score breakdowns and the run summary with its funnel (§10).
12. **Alert** the operator if a health check failed (§11).

## 4. Sources

Four sources are used. Remotive is not used: its public feed is small, delayed by 24 hours and ignores its own filters. The queries below are defaults; a fork replaces them in settings.

| Source | Endpoint style | Queries (configurable) | Requests/day |
|---|---|---|---|
| **Himalayas** (primary) | JSON search API: `/jobs/api/search` with `q`, `sort=recent`, `page`; 20 jobs per page | `backend engineer`, `tech lead`, `python` | 3 |
| **Jobicy** | JSON API: `/api/v2/remote-jobs`; up to 100 jobs per call | `industry=engineering` with `geo=apac`, and with `geo=anywhere`; no keyword | 2 |
| **RemoteOK** | JSON API filtered by comma-separated tags; roughly the latest 100 per tag | `tags=python,golang`, `tags=backend` | 2 |
| **We Work Remotely** | RSS per category; no search | Back-End feed, DevOps feed | 2 |

About nine requests a day in total.

### 4.1 Query behaviour to confirm during the build

The queries live in configuration, so adjusting them is a config change, not a code change. Three behaviours are confirmed by trial calls before the queries are finalized:

- Whether a multi-word Himalayas `q` means AND or OR.
- Whether a multi-tag RemoteOK filter (`python,golang`) means AND or OR.
- What Himalayas does with a `country=India` filter, and whether it is worth using.

### 4.2 Pagination

- Fetch one page per query, sorted by most recent.
- Fetch the next page only if every job on the current page is new (not already stored).
- Never fetch more than 3 pages per query (configurable cap).

### 4.3 Etiquette

- A fixed, descriptive User-Agent on every request.
- A small delay between requests to the same source.
- Exponential backoff on HTTP 429 and transient 5xx responses.
- No live API calls in tests; tests use recorded fixtures.

### 4.4 Attribution

- Every job keeps its source listing URL (`source_url`).
- Each job in the email names its source (`via Himalayas`).
- Before Job Digest ever becomes a public newsletter, each source's terms on redistribution are rechecked.

### 4.5 Source-specific location data

- **Himalayas:** `locationRestrictions` and `timezoneRestrictions`; an empty list means worldwide / any timezone.
- **RemoteOK:** free-text location field.
- **Jobicy:** geo field from the API.
- **WWR:** region text inside the RSS item.

## 5. Normalization

### 5.1 Job fields

Every listing, whatever its source, is converted into this shape. All labels are stored even when the email does not show them.

| Field | Meaning |
|---|---|
| `source` | Source identifier (`himalayas`, `jobicy`, `remoteok`, `wwr`) |
| `source_job_id` | The source's own ID for the listing |
| `source_url` | The listing page on the board (attribution) |
| `apply_url` | Direct apply link |
| `title` | Title as published |
| `title_normalized` | Normalized title (§5.2) |
| `company` | Company as published |
| `company_normalized` | Lowercased, punctuation-free company name |
| `employment_type` | Full-time, contract, etc. |
| `seniority` | From the source's field if present, otherwise from title keywords |
| `regions` | List of eligible regions/countries; empty when unparseable (shown as `–`) |
| `timezone_restriction` | Stored as published; unused in v1 scoring |
| `pay_min`, `pay_max` | Numbers when listed |
| `currency` | As listed; never converted |
| `pay_period` | `hour`, `month` or `year` |
| `pay_raw` | Original pay text |
| `posted_at` | Publication time (UTC) |
| `first_seen_at`, `last_seen_at` | When Job Digest first and last saw the listing (UTC) |
| `description` | Plain text; stripped after the retention period (§10.3) |
| `tags` | Source tags |
| `also_on` | Other sources where the same job appeared (§5.4) |

Per-user results of evaluation (status, score, matched skills, exclusion reason, config version) are stored separately from the job itself; see §10.

### 5.2 Title normalization

- Lowercase.
- Expand abbreviations: `Sr.` / `Sr` → `senior`, `Jr.` → `junior`, `Eng.` → `engineer`, and similar.
- Strip location and remote suffixes such as `(Remote)`, `– India`, `- Remote, APAC`.
- Ignore punctuation and collapse whitespace.

### 5.3 Seniority

Taken from the source's structured field when one exists. Otherwise inferred from title keywords (`senior`, `staff`, `lead`, `principal`, and so on).

### 5.4 Deduplication

- Two listings are the same job when their **normalized company** and **normalized title** both match. There is no date condition.
- The richest copy is kept: one with pay listed and regions parsed beats one without.
- The other copies are recorded in the kept job's `also_on` field.

### 5.5 Closed jobs

A job is marked `closed` only when its source returns a complete feed (one that lists every open job) and the job is missing from a successful fetch. Each source adapter declares `complete_feed`, `false` by default; it is set to `true` only after a trial confirms the feed is complete (milestones 2–3).

Sources that return only a recent window (typically Himalayas, RemoteOK and Jobicy) never close jobs: a job missing from them has most likely aged out of the window, not closed. A failed or empty fetch never closes anything. For those sources the 30-day age gate (§6) limits how long a job can stay a candidate.

## 6. Gates (hard filters)

A job that fails any gate is stored with status `excluded` and an `exclusion_reason` naming the gate. The excluded role types, levels and languages come from the profile (`exclude`; see `profile.example.yaml`). A job passes only if all of these hold:

1. It is remote.
2. It is open to the user's eligible regions, or its regions are unknown (§6.2).
3. Its title does not name an excluded role type (`exclude.roles`, for example frontend or full-stack).
4. Its title does not name an excluded level (`exclude.levels`, for example principal).
5. Its title does not name an excluded language (`exclude.title_languages`).
6. It was posted within `max_age_days` (30 by default).
7. It is not closed.
8. It has never been sent to this user before.

### 6.1 Role domain

- The target domain is defined by the profile's role tiers (§7.1), not by a separate gate. A job whose title matches no tier gets 0 role points and normally falls below `min_fit`, so unrelated roles drop out at selection.
- A skill is never a domain: a job that mentions a skill but matches no role tier must not qualify on the skill alone. `validate-profile` warns if `min_fit` is low enough for that to happen (§7).
- All employment types are included.
- Levels are included or excluded through `exclude.levels`.

### 6.2 Region eligibility

Eligible regions come from the profile (`eligible_regions`): for example the user's country, its wider regions, and Worldwide/Anywhere.

1. Use the source's structured location fields first.
2. Then run a keyword pass over the description for restrictions such as "US only", "EU", "must reside in", and timezone phrases.
3. Drop a job only when regions were parsed **and** none of them is eligible.
4. If nothing can be parsed, store an empty region list (shown as `–`) and keep the job.
5. Record where the regions came from (`region_source`: structured field, description keywords, or none), so parser quality can be measured.

The share of jobs ending up as `–` is measured during the build (milestone 5) to judge whether the parser is good enough.

## 7. Scoring

Jobs that pass the gates are scored from 0 to 100. Every point value below is a default that the profile can override (`scoring`).

| Component | Points | What it measures |
|---|---|---|
| Role fit | up to 40 | How well the title matches the roles the user wants |
| Skills fit | up to 40 | How much of the user's weighted skills the job asks for |
| Completeness | up to 20 | Region known (10) and pay listed (10) |
| Other-language penalty | −20 | Subtracted from fit (§7.5) |

```
fit   = clamp(role_fit + skills_fit − language_penalty, 0, 80)
total = fit + completeness                      (0–100)
```

`min_fit` (§8) is checked against `fit`, never against `total`. Completeness cannot rescue a weak match; it only lifts complete listings above incomplete ones. `validate-profile` warns when `min_fit` is low enough that skills alone (without a role match) could reach it.

Each evaluation stores the `profile_version` that produced it and the full breakdown (§7.6).

### 7.1 Role fit (up to 40)

The profile lists role tiers, each with points and titles. A job gets the points of the highest tier whose title matches its normalized title (§5.2). A title that matches no tier gets 0. Leadership roles (tech lead, staff, engineering manager) are ordinary tiers; where they sit is the user's choice.

Illustrative shape; the real tiers live in the profile:

| Tier | Points | Example titles |
|---|---|---|
| Exact | 40 | Tech Lead, Staff Engineer, Engineering Manager |
| Generic senior | 30 | Senior Software Engineer |
| Adjacent | 18 | Senior SRE, Senior Data Engineer |
| No seniority | 10 | Backend Engineer |

### 7.2 Skills fit (up to 40)

Each skill in the profile has a `weight`, optional aliases and optional matching options (§7.3).

```
matched_weight = Σ weight(skill) × location_factor(skill)
skills_fit     = 40 × min(1, matched_weight / skills_saturation)
```

- **Saturation, not a share of everything.** A listing names a handful of skills, not all of the user's. `skills_saturation` is the matched weight that already counts as a full match. Default: half of the total weight; calibrated in milestone 6.
- **Location factor.** 1.0 when the skill appears in the title or tags; 0.5 when it appears only in the description; 0.25 when it appears only inside a "nice to have", "bonus" or "preferred" part of the description.
- Each skill counts once.
- **Weights** express how safely the user can discuss a skill: high for strong skills, low or zero for skills only touched briefly.

### 7.3 Matching rules and checks

No LLM is involved at send time, so keyword matching must be conservative and tested.

- Matching is on word boundaries, never substrings, and case-insensitive by default.
- A generic word is never an alias on its own. "distributed" appears in "we are a distributed team"; the alias is "distributed systems". "agents" also matches "customer support agents"; the alias is "AI agents" or "LLM agents".
- Per-skill options for ambiguous names: `case_sensitive` (a short name such as `Go`), `require_near` (a context word that must appear close by), and `scope: title_tags` (count only title or tag matches; for vendor names that appear in company blurbs).
- **Fixture checks:** a test suite holds known false positives that must not match ("remote-first distributed team", "go-to-market", "customer support agents") and known true positives. Every false positive found while calibrating is added as a fixture before the rule is changed.

### 7.4 Completeness (up to 20)

- **Region known (10):** the job's regions explicitly include one of the profile's eligible regions. Unknown regions (`–`) get 0.
- **Pay listed (10):** any pay is listed. Amounts are never compared in v1.

### 7.5 Other-language penalty (−20)

Applied to fit when the description requires another programming language and mentions none of the profile's `primary_languages`. "X or Y" style requirements that include a primary language get no penalty.

The split between gates and penalties is deliberate: an excluded language **in the title** is a gate (§6); a different language **required in the description** is a penalty.

### 7.6 Score breakdown

Every evaluation stores a breakdown: the matched role tier and points, each matched skill with where it matched and its factor, the completeness parts, the penalty, `fit`, `total` and the region source. `dry-run` and the `explain` command print it (§12). Breakdowns are stored, never logged (SECURITY.md).

---

## 8. Selection

1. **Recent bucket first:** jobs posted within the last 7 days (configurable).
2. Only if the recent bucket holds fewer than 10 jobs, add jobs posted 8–30 days ago.
3. Drop jobs whose `fit` (§7) is below `min_fit` (configurable; calibrated with dry runs in milestone 6).
4. Sort by total score; break ties by newer `posted_at`.
5. Take the top 10.
6. Never include a job already sent to this user (sent history keyed by `user_id` + job).

On a thin day, send whatever qualifies, with a note at the top. On an empty day, send a short "no matches today" email.

Selected jobs become `sent`. Jobs that passed the gates but were not selected become `eligible_not_sent` and remain candidates for later days while they are within 30 days.

## 9. Email

### 9.1 Delivery

- One email per day, around 7:45 AM IST (02:15 UTC; GitHub may start scheduled runs late).
- One separate email per recipient; recipients never see each other's addresses.
- Sent over SMTP. A simple setup sends from the owner's own Gmail to the owner's own address with an app password (see ARCHITECTURE.md).

### 9.2 Content

The layout is compact. Per job:

- **Line 1:** job title (linked to the apply page) — company · score.
- **Line 2:** employment type · seniority · regions (`–` if unknown) · pay with period · age (`3d ago`) · `via <source>`.
- **Line 3:** matched skills.

Around the list:

- **Thin-day note** at the top when fewer than 10 jobs qualify.
- **Source-failure footer** naming any source that failed today.
- Older jobs (8–30 days) are not in a separate section; their age label marks them.
- The score is shown after the company name.

Illustrative shape:

```
Staff Backend Engineer — Acme · 72
Full-time · Staff · Worldwide · $150–180k/yr · 1d ago · via Himalayas
Python, Go, AWS

Senior Software Engineer — Foo · 58
Contract · Senior · APAC · $70–90/hr · 12d ago · via WWR
Python, Postgres
──────────
Himalayas was unavailable today.
```

### 9.3 Template — to be discussed

The exact template (subject wording, HTML vs. plain-text styling, the thin-day and empty-day wording) is still to be discussed and is settled in milestone 7. Until then, the content in §9.2 is the agreed baseline.

### 9.4 Time display

Everything is stored in UTC and converted to the profile's timezone (`Asia/Kolkata` for the owner) only when rendering.

## 10. Storage

### 10.1 What is stored

Every fetched job is stored, regardless of score. There is no storage threshold.

| Table | Holds |
|---|---|
| `jobs` | One row per deduplicated job (fields in §5.1) |
| `job_evaluations` | Per `user_id` + job: `status`, `fit`, `score`, `score_breakdown` (JSON), `matched_skills`, `exclusion_reason`, `region_source`, `profile_version`, `evaluated_at` |
| `sent_history` | Per `user_id` + job: when it was sent and in which run |
| `runs` | One row per run: start/end time, outcome, per-source fetch stats (counts, HTTP status, duration), the funnel (§10.5), counts per status |

### 10.2 Statuses

| Status | Meaning |
|---|---|
| `sent` | Included in a digest |
| `eligible_not_sent` | Passed the gates but not selected (yet) |
| `excluded` | Failed a gate; `exclusion_reason` says which |
| `closed` | No longer in its source feed |

### 10.3 Retention

- Job descriptions are stripped after about 90 days (configurable). All other fields are kept.
- Old records stay queryable from the CLI.

### 10.4 Profile versioning

The profile carries a `profile_version`. Every score stores the version that produced it, so a change in weights can be traced to its effect on results.

### 10.5 Observability

Tuning needs data, so the database keeps what logs may not (SECURITY.md):

- **Per evaluation:** the score breakdown (§7.6) and the region source (§6.2).
- **Per run:** the funnel (fetched → deduplicated → excluded per gate → scored → below `min_fit` → selected → sent) and per-source stats (counts, HTTP status, duration).
- **Reading it:** through local read-only CLI commands (§12), which refuse to run inside GitHub Actions.

Public workflow logs carry only counts and non-identifying diagnostics such as gate names with counts, HTTP status codes and durations.

## 11. Operator alerts

Alerts are separate from the digest and never appear in it.

- Enabled by default (`alerts.enabled`, overridable by environment variable).
- Sent to `ALERT_TO`, falling back to `NOTIFY_TO` when unset.
- Triggered by:
  - a source returning zero jobs for 2–3 consecutive runs;
  - a failed database migration;
  - the database being unreachable (the email step does not need the database, so this alert can still be sent).
- After an alert, the workflow fails so GitHub's own failed-run notification also fires (an account setting).

## 12. Commands

| Command | What it does |
|---|---|
| `job-digest run` | The full daily pipeline (§3) |
| `job-digest dry-run` | Runs everything except sending; prints the email with scores. Local only — refuses to run inside GitHub Actions |
| `job-digest validate-profile` | Checks the profile for errors; also the first step of every workflow run |

Further read-only commands for querying stored data are added as needed, for example `job-digest explain <job>` (score breakdown) and `job-digest funnel` (recent runs). Any command that prints job content refuses to run inside GitHub Actions.

## 13. Open questions settled during the build

| Question | Settled in |
|---|---|
| AND/OR semantics of Himalayas and RemoteOK queries; Himalayas `country=India` | Milestones 2–3 |
| Turso driver for SQLAlchemy | Milestone 1 |
| Share of jobs with unknown regions | Milestone 5 |
| `min_fit` and `skills_saturation` values | Milestone 6 |
| Skill-matching false positives (fixture set) | Milestone 6 |
| Which sources return a complete feed (`complete_feed`) | Milestones 2–3 |
| Exact email template | Milestone 7 |
| Schedule keepalive mechanism | Milestone 8 |

# Job Digest — Privacy and Security

Job Digest lives in a public repository, and workflow logs on a public repository are public. Privacy is therefore enforced by guards at every layer, not by care alone.

## 1. What must never be public

- Credentials: database URL and token, SMTP username and password.
- Email addresses: recipients and alert addresses.
- The personal profile: skills, weights, roles, regions, score threshold.
- Job listings and digests: what was fetched, scored, excluded or sent.

None of these are ever committed, and none are ever written to workflow logs.

## 2. Guards

### 2.1 Pre-commit (local, before every commit)

- **gitleaks** scans staged changes for secrets.
- **Private-key detector** (`detect-private-key`).
- **Blocked-file hook** (`scripts/block_private_files.py`) rejects `.env`, `profile.yaml` and any `*.db` / `*.sqlite` / `*.sqlite3` file, even if `.gitignore` is bypassed with `git add -f`.

### 2.2 CI (every push and pull request)

- **gitleaks** over the full git history.
- **zizmor** audits workflow files for over-broad permissions and unsafe triggers.
- **pip-audit** checks dependencies for known vulnerabilities.
- **CodeQL** code scanning (free for public repositories).

### 2.3 GitHub repository settings

- Secret scanning with **push protection**, which rejects pushes containing known secret formats.
- **Dependabot** for dependency and Actions updates.
- Default workflow token permissions set to read-only; each workflow requests only what it needs.
- Pull requests from forks never receive secrets.
- Third-party Actions pinned to full commit SHAs.
- Private vulnerability reporting enabled (§4).

### 2.4 Runtime

- **Log masking filter:** every log record passes through a filter that masks profile values, credentials and email addresses. GitHub masks registered secret values, but only exact matches; values derived from them (a single skill out of the profile YAML, an address inside a sentence) are caught by this filter.
- **Counts only:** logs report counts ("himalayas: 47 fetched, 12 new") and non-identifying diagnostics such as gate names with counts, HTTP status codes and durations. Never titles, companies, scores, score breakdowns or addresses. Analysis data lives in the database and is read through local commands (SPEC §10.5).
- **Content commands refuse in Actions:** `dry-run` and any other command that prints job content detect GitHub Actions (`GITHUB_ACTIONS=true`) and exit with an error.
- **Leak test:** a test runs the pipeline on fixtures with a sample profile and fails the build if any profile value or address appears in captured log output.

## 3. Fork owners

- Put credentials and the profile only in your fork's GitHub Secrets (and a local, git-ignored `.env` / `profile.yaml`).
- Enable secret scanning and push protection in your fork's settings.
- Install the pre-commit hooks before making changes: `uv run pre-commit install`.
- Your fork is public too: treat its logs as public.

## 4. Reporting a vulnerability

Please report security issues privately through GitHub's **"Report a vulnerability"** button on the repository's Security tab, rather than in a public issue.

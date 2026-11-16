# Job Digest — How-to Guide

Practical, task-oriented steps for running and maintaining a Job Digest repository. This guide grows as features land; for what the app does see [SPEC.md](SPEC.md), for how it is built see [ARCHITECTURE.md](ARCHITECTURE.md), and for the privacy guards see [SECURITY.md](SECURITY.md).

> **Status:** stub. Only the repository security setup is written so far. Planned sections are listed at the end.

---

## Repository security setup (GitHub settings)

All of these are free on public repositories. Secret scanning and push protection are on by default for public repositories; the rest must be switched on once per repository (and once per fork).


| Setting                                 | Why                                                   | Free on public repos |
| ----------------------------------------- | ------------------------------------------------------- | ---------------------- |
| Secret scanning                         | Flags known secret formats already in the repository  | Yes                  |
| Push protection                         | Rejects a push that contains a known secret           | Yes                  |
| Private vulnerability reporting         | Lets people report issues privately (SECURITY.md §4) | Yes                  |
| Dependabot alerts                       | Warns about vulnerable dependencies                   | Yes                  |
| Dependabot security updates             | Opens pull requests that fix vulnerable dependencies  | Yes                  |
| Default workflow permissions: read-only | A workflow gets write access only if it asks for it   | Yes                  |

### Turn them on with the GitHub CLI

Replace `OWNER/REPO` with your repository (for a fork, your fork).

```bash
# Private vulnerability reporting
gh api -X PUT repos/OWNER/REPO/private-vulnerability-reporting

# Dependabot alerts, then security updates
gh api -X PUT repos/OWNER/REPO/vulnerability-alerts
gh api -X PUT repos/OWNER/REPO/automated-security-fixes

# Secret scanning and push protection (already on for public repositories)
gh api -X PATCH repos/OWNER/REPO --input - <<'JSON'
{"security_and_analysis": {
  "secret_scanning": {"status": "enabled"},
  "secret_scanning_push_protection": {"status": "enabled"}
}}
JSON

# Default workflow permissions: read-only
gh api -X PUT repos/OWNER/REPO/actions/permissions/workflow \
  -f default_workflow_permissions=read \
  -F can_approve_pull_request_reviews=false
```

### Check the result

```bash
gh api repos/OWNER/REPO/private-vulnerability-reporting --jq .enabled
gh api repos/OWNER/REPO --jq '.security_and_analysis'
gh api repos/OWNER/REPO/actions/permissions/workflow
```

Expect `true`, every status `enabled`, and `"default_workflow_permissions":"read"`.

---

## Planned sections

- Fork, configure and run your own copy (today: README, "Run your own copy").
- Write and tune your profile: weights, role tiers, skill-matching options, `min_fit`.
- Read a dry run and calibrate with `explain` and `funnel`.
- Add a source, notifier or renderer.
- Troubleshoot a failed or silent run.

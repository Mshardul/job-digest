"""Pre-commit hook: refuse to commit private files, even with `git add -f`.

Receives the staged file paths as arguments and exits non-zero, naming each
offending path, if any of them is a private file (see docs/SECURITY.md).
"""

from __future__ import annotations

import sys
from fnmatch import fnmatch
from pathlib import PurePosixPath

BLOCKED = (
    ".env",
    ".env.*",
    "profile.yaml",
    "profile.*.yaml",
    "*.db",
    "*.db-journal",
    "*.db-wal",
    "*.db-shm",
    "*.sqlite",
    "*.sqlite3",
)
ALLOWED = (".env.example", "profile.example.yaml")


def is_blocked(path: str) -> bool:
    name = PurePosixPath(path.replace("\\", "/")).name
    if name in ALLOWED:
        return False
    return any(fnmatch(name, pattern) for pattern in BLOCKED)


def main(argv: list[str]) -> int:
    blocked = [path for path in argv if is_blocked(path)]
    for path in blocked:
        print(f"Blocked private file: {path}", file=sys.stderr)
    if blocked:
        print(
            "These files must never be committed. Unstage them with "
            "`git restore --staged <file>`.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

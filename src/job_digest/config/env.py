"""Environment variable checks for Job Digest."""

from __future__ import annotations

import os
from collections.abc import Iterable


class MissingRequiredEnvVarsError(RuntimeError):
    """Raised when required environment variables are missing."""

    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        names = ", ".join(missing)
        super().__init__(f"Missing required environment variable(s): {names}")


def find_missing_env_vars(required: Iterable[str]) -> list[str]:
    missing: list[str] = []
    for name in required:
        value = os.getenv(name)
        if value is None or value == "":
            missing.append(name)
    return missing


def ensure_required_env_vars(required: Iterable[str]) -> None:
    missing = find_missing_env_vars(required)
    if missing:
        raise MissingRequiredEnvVarsError(missing)

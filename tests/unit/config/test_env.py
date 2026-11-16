from __future__ import annotations

import pytest

from job_digest.config.env import (
    MissingRequiredEnvVarsError,
    ensure_required_env_vars,
    find_missing_env_vars,
)


def test_find_missing_env_vars_names_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRESENT", "1")
    monkeypatch.delenv("MISSING_ONE", raising=False)
    monkeypatch.setenv("EMPTY_ONE", "")
    missing = find_missing_env_vars(["PRESENT", "MISSING_ONE", "EMPTY_ONE"])
    assert missing == ["MISSING_ONE", "EMPTY_ONE"]


def test_ensure_required_env_vars_stops_and_names_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    with pytest.raises(MissingRequiredEnvVarsError) as exc:
        ensure_required_env_vars(["DATABASE_URL", "SMTP_HOST"])
    message = str(exc.value)
    assert "DATABASE_URL" in message
    assert "SMTP_HOST" in message
    assert "Missing required environment variable(s)" in message


def test_ensure_required_env_vars_passes_when_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///x.db")
    ensure_required_env_vars(["DATABASE_URL"])

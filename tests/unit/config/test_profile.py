from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml

from job_digest.config.profile import PROFILE_ENV_VAR, load_profile, validate_profile


def _load_example() -> dict[str, Any]:
    data = yaml.safe_load(Path("profile.example.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_example_profile_validates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PROFILE_ENV_VAR, yaml.safe_dump(_load_example()))
    errors, warnings = validate_profile()
    assert errors == []
    assert warnings == []


def test_loads_from_env_string(monkeypatch: pytest.MonkeyPatch) -> None:
    data = _load_example()
    monkeypatch.setenv(PROFILE_ENV_VAR, yaml.safe_dump(data))
    profile = load_profile()
    assert profile.user_id == data["user_id"]
    assert profile.profile_version == data["profile_version"]


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda d: d.pop("user_id"), "user_id"),
        (lambda d: d.pop("profile_version"), "profile_version"),
        (lambda d: d.update({"profile_version": 0}), "profile_version"),
        (lambda d: d.update({"role_tiers": []}), "role_tiers"),
        (lambda d: d.update({"eligible_regions": []}), "eligible_regions"),
        (lambda d: d.update({"timezone": ""}), "timezone"),
        (lambda d: d.update({"min_fit": -1}), "min_fit"),
        (lambda d: d.update({"extra_field": 1}), "extra_field"),
    ],
)
def test_invalid_profiles_report_specific_error(
    monkeypatch: pytest.MonkeyPatch,
    mutate: Any,
    expected: str,
) -> None:
    data = deepcopy(_load_example())
    mutate(data)
    monkeypatch.setenv(PROFILE_ENV_VAR, yaml.safe_dump(data))
    errors, _ = validate_profile()
    assert errors
    assert any(expected in err for err in errors)


def test_invalid_yaml_reports_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PROFILE_ENV_VAR, ": [unterminated")
    errors, _ = validate_profile()
    assert errors
    assert any("not valid YAML" in err for err in errors)


def test_empty_profile_reports_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PROFILE_ENV_VAR, "")
    errors, _ = validate_profile()
    assert errors
    assert any("empty" in err.lower() for err in errors)


def test_min_fit_at_or_below_skills_fit_warns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = deepcopy(_load_example())
    data["min_fit"] = data["scoring"]["skills_fit"]
    monkeypatch.setenv(PROFILE_ENV_VAR, yaml.safe_dump(data))
    errors, warnings = validate_profile()
    assert errors == []
    assert any("skills alone could qualify" in w for w in warnings)
    assert any("§6.1" in w or "6.1" in w for w in warnings)

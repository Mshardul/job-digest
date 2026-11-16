from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from job_digest.cli import main
from job_digest.config.profile import PROFILE_ENV_VAR


def _load_example() -> dict[str, object]:
    data = yaml.safe_load(Path("profile.example.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_validate_profile_success(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(PROFILE_ENV_VAR, yaml.safe_dump(_load_example()))
    code = main(["validate-profile"])
    captured = capsys.readouterr()
    assert code == 0
    assert "Profile is valid." in captured.out
    assert captured.err == ""


def test_validate_profile_failure_is_specific_and_nonzero(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    data = deepcopy(_load_example())
    data.pop("user_id")
    monkeypatch.setenv(PROFILE_ENV_VAR, yaml.safe_dump(data))
    code = main(["validate-profile"])
    captured = capsys.readouterr()
    assert code == 1
    assert "user_id" in captured.err
    assert "Error:" in captured.err
    # must not echo profile values beyond field names
    assert "me" not in captured.out
    assert "me" not in captured.err


def test_validate_profile_warns_for_low_min_fit(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    data = deepcopy(_load_example())
    data["min_fit"] = data["scoring"]["skills_fit"]
    monkeypatch.setenv(PROFILE_ENV_VAR, yaml.safe_dump(data))
    code = main(["validate-profile"])
    captured = capsys.readouterr()
    assert code == 0
    assert "Profile is valid." in captured.out
    assert "Warning:" in captured.err
    assert "skills alone could qualify" in captured.err

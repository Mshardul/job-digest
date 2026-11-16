"""Profile model and validation for Job Digest."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

PROFILE_ENV_VAR = "JOB_DIGEST_PROFILE"
PROFILE_FILE = Path("profile.yaml")


class RoleTier(BaseModel):
    model_config = ConfigDict(extra="forbid")

    points: int = Field(ge=0, le=40)
    titles: list[str] = Field(min_length=1)

    @field_validator("titles")
    @classmethod
    def titles_not_blank(cls, value: list[str]) -> list[str]:
        if any(not title.strip() for title in value):
            raise ValueError("titles must not contain blank values")
        return value


class Skill(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    weight: float = Field(ge=0)
    aliases: list[str] = Field(default_factory=list)
    case_sensitive: bool = False
    require_near: list[str] | str | None = None
    scope: Literal["title_tags"] | None = None

    @field_validator("aliases")
    @classmethod
    def aliases_not_blank(cls, value: list[str]) -> list[str]:
        if any(not alias.strip() for alias in value):
            raise ValueError("aliases must not contain blank values")
        return value


class Exclude(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roles: list[str] = Field(default_factory=list)
    levels: list[str] = Field(default_factory=list)
    title_languages: list[str] = Field(default_factory=list)

    @field_validator("roles", "levels", "title_languages")
    @classmethod
    def values_not_blank(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("must not contain blank values")
        return value


class Scoring(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_fit: int = Field(default=40, ge=0)
    skills_fit: int = Field(default=40, ge=0)
    region_known: int = Field(default=10, ge=0)
    pay_listed: int = Field(default=10, ge=0)
    language_penalty: int = Field(default=20, ge=0)


class Profile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version: int = Field(ge=1)
    user_id: str = Field(min_length=1)
    timezone: str = Field(min_length=1)
    eligible_regions: list[str] = Field(min_length=1)
    role_tiers: list[RoleTier] = Field(min_length=1)
    skills: list[Skill] = Field(default_factory=list)
    skills_saturation: float | None = Field(default=None, gt=0)
    exclude: Exclude = Field(default_factory=Exclude)
    primary_languages: list[str] = Field(default_factory=list)
    scoring: Scoring = Field(default_factory=Scoring)
    min_fit: int = Field(ge=0)

    @field_validator("eligible_regions", "primary_languages")
    @classmethod
    def string_items_not_blank(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("must not contain blank values")
        return value

    @model_validator(mode="after")
    def default_skills_saturation(self) -> Profile:
        if self.skills_saturation is None:
            total_weight = sum(skill.weight for skill in self.skills)
            self.skills_saturation = total_weight / 2 if total_weight > 0 else 1.0
        return self


def format_validation_error(error: ValidationError) -> list[str]:
    messages: list[str] = []
    for item in error.errors():
        location = ".".join(str(part) for part in item["loc"]) or "profile"
        msg = item["msg"]
        if msg.startswith("Value error, "):
            msg = msg.removeprefix("Value error, ")
        messages.append(f"{location}: {msg}")
    return messages


def load_profile_data() -> tuple[dict[str, Any], str]:
    raw_env = os.getenv(PROFILE_ENV_VAR)
    if raw_env is not None:
        source = PROFILE_ENV_VAR
        try:
            data = yaml.safe_load(raw_env)
        except yaml.YAMLError as exc:
            raise ValueError(
                f"{source} is not valid YAML: {exc.__class__.__name__}"
            ) from exc
    else:
        source = str(PROFILE_FILE)
        if not PROFILE_FILE.exists():
            raise FileNotFoundError(f"Profile file not found: {PROFILE_FILE}")
        try:
            text = PROFILE_FILE.read_text(encoding="utf-8")
        except OSError as exc:
            raise OSError(f"Could not read profile file: {PROFILE_FILE}") from exc
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ValueError(f"Profile file is not valid YAML: {PROFILE_FILE}") from exc

    if data is None:
        raise ValueError(f"Profile is empty: {source}")
    if not isinstance(data, dict):
        raise ValueError(f"Profile must be a mapping: {source}")
    return data, source


def load_profile() -> Profile:
    data, _ = load_profile_data()
    try:
        return Profile.model_validate(data)
    except ValidationError as exc:
        raise ValueError("\n".join(format_validation_error(exc))) from exc


def validate_profile() -> tuple[list[str], list[str]]:
    try:
        data, _ = load_profile_data()
    except (FileNotFoundError, OSError, ValueError) as exc:
        return [str(exc)], []

    try:
        profile = Profile.model_validate(data)
    except ValidationError as exc:
        return format_validation_error(exc), []

    warnings: list[str] = []
    if profile.min_fit <= profile.scoring.skills_fit:
        warnings.append(
            "min_fit is at or below scoring.skills_fit; skills alone could qualify "
            "(SPEC §6.1)."
        )
    return [], warnings

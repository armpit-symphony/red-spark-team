from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


ModeType = Literal["exploratory", "consent_gated"]
TargetType = Literal["repo", "webapp", "script", "service"]


class TargetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    target_type: TargetType
    locator: str = Field(min_length=3, max_length=300)
    scope_limit: str = Field(min_length=5, max_length=400)
    allowed_modes: list[ModeType]
    notes: str = Field(default="", max_length=2000)


class PolicyUpdate(BaseModel):
    passive_rules: list[str]
    deep_mode_requirements: list[str]
    deep_mode_consent_token: str = Field(min_length=4, max_length=80)
    export_requires_review: bool = True
    secret_redaction_enabled: bool = True
    deny_by_default_egress: bool = True


class ProviderUpdate(BaseModel):
    model: str = Field(min_length=2, max_length=120)
    enabled: bool
    auth_mode: Literal["universal", "custom"]
    base_url: str = ""
    custom_api_key: str = ""


class RunCreate(BaseModel):
    target_id: str
    mode: ModeType
    objective: str = Field(min_length=4, max_length=500)
    scope_notes: str = Field(default="", max_length=2000)
    consent_token: str = Field(default="", max_length=120)


class SectionUpsert(BaseModel):
    section_key: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=120)
    content: str = Field(default="", max_length=40000)
    format: Literal["markdown", "text", "json"] = "text"


class AnalysisRequest(BaseModel):
    provider: Literal["openai", "anthropic", "openrouter", "minimax"]
    model: str = Field(min_length=2, max_length=120)
    analysis_type: Literal["finding_summary", "report_draft", "remediation_plan"]
    focus: str = Field(default="", max_length=500)

"""Response models exposed by the College Guidance API."""

from pydantic import BaseModel, Field
from typing import Literal


class HealthResponse(BaseModel):
    status: str
    service: str


class ProfileResponse(BaseModel):
    id: str
    display_name: str
    display_name_en: str
    display_name_zh: str


class ProfilesResponse(BaseModel):
    profiles: list[ProfileResponse]


class ModeResponse(BaseModel):
    id: str
    title_en: str
    title_zh: str


class ModesResponse(BaseModel):
    modes: list[ModeResponse]


class RecommendationTurn(BaseModel):
    role: str
    content: str = Field(max_length=20_000)


class RecommendationRequest(BaseModel):
    profile_id: str
    mode: str
    language: str = "en"
    query: str = Field(default="", max_length=5_000)
    college_preferences: "CollegePreferences | None" = None
    college_scenario: str | None = None
    history: list[RecommendationTurn] = Field(default_factory=list, max_length=8)


class ProfileAddition(BaseModel):
    experience_number: int | None = Field(default=None, ge=1)
    experience_title: str | None = Field(default=None, max_length=300)
    action: str = Field(default="", max_length=5_000)
    outcome: str = Field(default="", max_length=5_000)
    reflection: str = Field(default="", max_length=5_000)
    source: Literal["user_confirmed"] = "user_confirmed"


class ProfileAdditionPreviewRequest(BaseModel):
    profile_id: str
    question: str = Field(max_length=5_000)
    answer: str = Field(max_length=5_000)


class ProfileAdditionSaveRequest(BaseModel):
    profile_id: str
    addition: ProfileAddition
    confirm_warnings: bool = False


class ProfileAdditionRecord(ProfileAddition):
    id: str
    confirmed_at: str


class ProfileEvidenceSource(BaseModel):
    kind: Literal["original_profile", "user_confirmed"]
    label: str
    record_id: str | None = None
    confirmed_at: str | None = None


class StructuredExperience(BaseModel):
    experience_number: int | None = None
    experience_title: str
    category: str = ""
    background: str = ""
    challenge: str = ""
    action: str = ""
    outcome: str = ""
    reflection: str = ""
    traits: list[str] = Field(default_factory=list)
    missing_fields: list[Literal["action", "outcome", "reflection"]] = Field(default_factory=list)
    status: Literal["documented", "enriched", "user_confirmed"]
    sources: list[ProfileEvidenceSource] = Field(default_factory=list)
    additions: list[ProfileAdditionRecord] = Field(default_factory=list)


class StructuredStudentProfile(BaseModel):
    profile_id: str
    profile_name: str
    academic_interests: list[str] = Field(default_factory=list)
    background: list[str] = Field(default_factory=list)
    core_themes: list[str] = Field(default_factory=list)
    experiences: list[StructuredExperience] = Field(default_factory=list)


class CollegePreferences(BaseModel):
    sat: int | None = Field(default=None, ge=400, le=1600)
    act: int | None = Field(default=None, ge=1, le=36)
    states: str = "CA"
    max_cost: float | None = Field(default=None, gt=0)
    size: list[str] = ["any"]
    ownership: list[str] = ["any"]
    institution_format: list[str] = ["either"]
    competition: list[str] = ["any"]
    admission_rate_min: int = Field(default=0, ge=0, le=100)
    admission_rate_max: int = Field(default=100, ge=0, le=100)
    field: str = "Computer Science"
    targets: str = "No specific target"
    count: int = Field(default=5, ge=1, le=20)


class ChatRequest(BaseModel):
    session_id: str | None = None
    profile_id: str
    language: str = "en"
    message: str = Field(default="", max_length=5_000)
    choice_id: str | None = None


class QuickReply(BaseModel):
    id: str
    label: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    ready: bool
    preferences: CollegePreferences
    answered: list[str]
    scenario: str | None = None
    quick_replies: list[QuickReply] = Field(default_factory=list)
    awaiting: str | None = None
    session_reset: bool = False

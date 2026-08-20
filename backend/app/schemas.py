"""Response models exposed by the College Guidance API."""

from pydantic import BaseModel, Field


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

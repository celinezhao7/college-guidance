"""Response models exposed by the College Guidance API."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


class ProfileResponse(BaseModel):
    id: str
    display_name: str


class ProfilesResponse(BaseModel):
    profiles: list[ProfileResponse]


class ModeResponse(BaseModel):
    id: str
    title_en: str
    title_zh: str


class ModesResponse(BaseModel):
    modes: list[ModeResponse]

"""College Guidance FastAPI entry point.

This first API layer is intentionally read-only. It does not alter the existing
CLI, student documents, Chroma indexes, or recommendation modules.
"""

from fastapi import FastAPI

from .profile_service import list_profiles
from .schemas import (
    HealthResponse,
    ModeResponse,
    ModesResponse,
    ProfileResponse,
    ProfilesResponse,
)


app = FastAPI(
    title="College Guidance API",
    summary="Backend API for the College Guidance project",
    version="0.1.0",
)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "service": "College Guidance API",
        "version": app.version,
        "documentation": "/docs",
    }


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="college-guidance-api")


@app.get("/api/profiles", response_model=ProfilesResponse, tags=["profiles"])
def profiles() -> ProfilesResponse:
    return ProfilesResponse(
        profiles=[
            ProfileResponse(id=profile.id, display_name=profile.display_name)
            for profile in list_profiles()
        ]
    )


@app.get("/api/modes", response_model=ModesResponse, tags=["recommendations"])
def modes() -> ModesResponse:
    return ModesResponse(
        modes=[
            ModeResponse(
                id="uc_piq",
                title_en="UC PIQ Recommendation",
                title_zh="UC 个人洞察问题（PIQ）推荐",
            ),
            ModeResponse(
                id="common_app",
                title_en="Common App Essay Prompt Recommendation",
                title_zh="Common App 主文书题目推荐",
            ),
            ModeResponse(
                id="college_field",
                title_en="College and Field-of-Study Matching",
                title_zh="大学与专业领域匹配",
            ),
        ]
    )

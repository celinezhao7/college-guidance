"""College Guidance FastAPI entry point.

Exposes API endpoints for system metadata, student profiles,
recommendation modes, and streaming recommendation generation.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.recommend import is_student_profile_indexed, stream_recommendation

from .profile_service import get_profile, list_profiles
from .rate_limit import enforce_rate_limit
from .streaming import resilient_stream
from .conversation_service import chat as continue_conversation
from .schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ModeResponse,
    ModesResponse,
    ProfileResponse,
    ProfilesResponse,
    RecommendationRequest,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

app = FastAPI(
    title="College Guidance API",
    summary="Backend API for the College Guidance project",
    version="0.1.0",
)


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="college-guidance-api")


@app.get("/api/profiles", response_model=ProfilesResponse, tags=["profiles"])
def profiles() -> ProfilesResponse:
    return ProfilesResponse(
        profiles=[
            ProfileResponse(
                id=profile.id,
                display_name=profile.display_name,
                display_name_en=profile.display_name_en,
                display_name_zh=profile.display_name_zh,
            )
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


@app.post("/api/recommend", tags=["recommendations"])
def recommend(payload: RecommendationRequest, request: Request):
    enforce_rate_limit(request, "recommend")
    mode_map = {
        "uc_piq": "uc",
        "common_app": "common_app",
        "college_field": "college_major",
    }

    application_type = mode_map.get(payload.mode)

    if application_type is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported recommendation mode: {payload.mode}",
        )

    profile = get_profile(payload.profile_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Student profile not found.",
        )

    if not is_student_profile_indexed(profile.filename):
        raise HTTPException(
            status_code=409,
            detail=(
                "This student profile is not present in the Chroma index. "
                "Run 'python src/build_index.py' and try again."
            ),
        )

    def recommendation_factory():
        return stream_recommendation(
            profile_name=profile.filename,
            application_type=application_type,
            language=payload.language,
            query=payload.query,
            college_preferences=(
                payload.college_preferences.model_dump()
                if payload.college_preferences
                else None
            ),
            college_scenario=payload.college_scenario,
            history=[turn.model_dump() for turn in payload.history],
        )

    return StreamingResponse(
        resilient_stream(recommendation_factory, language=payload.language),
        media_type="text/plain",
    )


@app.post("/api/chat", response_model=ChatResponse, tags=["chat"])
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    enforce_rate_limit(request, "chat")
    if get_profile(payload.profile_id) is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return ChatResponse.model_validate(
        continue_conversation(
            session_id=payload.session_id,
            profile_id=payload.profile_id,
            language=payload.language,
            message=payload.message,
            choice_id=payload.choice_id,
        )
    )


if FRONTEND_DIST.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=FRONTEND_DIST, html=True),
        name="frontend",
    )
else:
    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "service": "College Guidance API",
            "version": app.version,
            "documentation": "/docs",
        }

"""College Guidance FastAPI entry point.

Exposes API endpoints for system metadata, student profiles,
recommendation modes, and streaming recommendation generation.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.recommend import is_student_profile_indexed, stream_recommendation

from .profile_service import get_profile, list_profiles
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


@app.post("/api/recommend", tags=["recommendations"])
def recommend(request: RecommendationRequest):
    mode_map = {
        "uc_piq": "uc",
        "common_app": "common_app",
        "college_field": "college_major",
    }

    application_type = mode_map.get(request.mode)

    if application_type is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported recommendation mode: {request.mode}",
        )

    profile = get_profile(request.profile_id)
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

    return StreamingResponse(
        stream_recommendation(
            profile_name=profile.filename,
            application_type=application_type,
            language=request.language,
            query=request.query,
            college_preferences=(
                request.college_preferences.model_dump()
                if request.college_preferences
                else None
            ),
            college_scenario=request.college_scenario,
        ),
        media_type="text/plain",
    )


@app.post("/api/chat", response_model=ChatResponse, tags=["chat"])
def chat(request: ChatRequest) -> ChatResponse:
    if get_profile(request.profile_id) is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return ChatResponse.model_validate(
        continue_conversation(
            session_id=request.session_id,
            profile_id=request.profile_id,
            language=request.language,
            message=request.message,
            choice_id=request.choice_id,
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

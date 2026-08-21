"""College Guidance FastAPI entry point.

Exposes API endpoints for system metadata, student profiles,
recommendation modes, and streaming recommendation generation.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from src.recommend import is_student_profile_indexed, stream_recommendation
from src.safety import SafetyAction, validate_input

from .profile_service import get_profile, list_profiles
from .profile_information import build_structured_profile
from .profile_additions import (
    delete_addition,
    format_additions,
    list_addition_records,
    preview_addition,
    save_addition,
    update_addition,
)
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
    ProfileAddition,
    ProfileAdditionPreviewRequest,
    ProfileAdditionSaveRequest,
    ProfileAdditionRecord,
    StructuredStudentProfile,
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
            profile_additions_context=format_additions(payload.profile_id),
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


@app.post("/api/profile-additions/preview", response_model=ProfileAddition, tags=["profiles"])
def profile_addition_preview(payload: ProfileAdditionPreviewRequest, request: Request):
    enforce_rate_limit(request, "chat")
    if get_profile(payload.profile_id) is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    safety = validate_input(payload.answer, "chat")
    if not safety.allowed or safety.action is SafetyAction.REDACT:
        raise HTTPException(status_code=400, detail="This answer cannot be added to the profile.")
    return preview_addition(payload.question, payload.answer)


@app.post("/api/profile-additions", tags=["profiles"])
def profile_addition_save(payload: ProfileAdditionSaveRequest, request: Request):
    enforce_rate_limit(request, "chat")
    if get_profile(payload.profile_id) is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    combined = "\n".join(
        [payload.addition.action, payload.addition.outcome, payload.addition.reflection]
    )
    safety = validate_input(combined, "student_kb")
    if not safety.allowed or safety.action is SafetyAction.REDACT:
        raise HTTPException(status_code=400, detail="This information cannot be saved.")
    return save_addition(payload.profile_id, payload.addition)


@app.get(
    "/api/profile-additions/{profile_id}",
    response_model=list[ProfileAdditionRecord],
    tags=["profiles"],
)
def profile_addition_list(profile_id: str):
    if get_profile(profile_id) is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return list_addition_records(profile_id)


@app.get(
    "/api/profiles/{profile_id}/information",
    response_model=StructuredStudentProfile,
    tags=["profiles"],
)
def structured_profile_information(profile_id: str):
    profile = get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return build_structured_profile(profile, list_addition_records(profile_id))


@app.put(
    "/api/profile-additions/{profile_id}/{addition_id}",
    response_model=ProfileAdditionRecord,
    tags=["profiles"],
)
def profile_addition_update(
    profile_id: str,
    addition_id: str,
    addition: ProfileAddition,
    request: Request,
):
    enforce_rate_limit(request, "chat")
    if get_profile(profile_id) is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    combined = "\n".join([addition.action, addition.outcome, addition.reflection])
    safety = validate_input(combined, "student_kb")
    if not safety.allowed or safety.action is SafetyAction.REDACT:
        raise HTTPException(status_code=400, detail="This information cannot be saved.")
    updated = update_addition(profile_id, addition_id, addition)
    if updated is None:
        raise HTTPException(status_code=404, detail="Profile addition not found.")
    return updated


@app.delete("/api/profile-additions/{profile_id}/{addition_id}", tags=["profiles"])
def profile_addition_delete(profile_id: str, addition_id: str, request: Request):
    enforce_rate_limit(request, "chat")
    if get_profile(profile_id) is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    if not delete_addition(profile_id, addition_id):
        raise HTTPException(status_code=404, detail="Profile addition not found.")
    return {"deleted": True}


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

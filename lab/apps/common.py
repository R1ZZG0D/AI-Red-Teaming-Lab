from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from lab.shared.challenges import CHALLENGES, DEFAULT_CHALLENGE_ID, challenge_by_id, public_challenges, validate_flag
from lab.shared.config import Settings
from lab.shared.database import initialize_lab_state
from lab.shared.schemas import ChatRequest, ChatResponse, FlagSubmissionRequest, FlagSubmissionResponse


def create_lab_app(settings: Settings, route_path: str, service: object) -> FastAPI:
    app = FastAPI(title=settings.app_name)
    templates = Jinja2Templates(directory=str(settings.base_dir / "lab" / "templates"))
    static_dir = settings.base_dir / "lab" / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    peer_path = "/secure" if route_path == "/vuln" else "/vuln"

    @app.on_event("startup")
    def startup() -> None:
        initialize_lab_state(settings)

    @app.get("/", include_in_schema=False)
    def index() -> RedirectResponse:
        return RedirectResponse(url=route_path)

    @app.get(route_path, response_class=HTMLResponse)
    def render_ui(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "student.html",
            {
                "title": settings.app_name,
                "mode": settings.app_mode,
                "route_path": route_path,
                "peer_path": peer_path,
                "debug_path": f"{route_path}/debug",
                "default_challenge_id": DEFAULT_CHALLENGE_ID,
                "challenges": public_challenges(),
                "flag_format": "ENPM604{...}",
                "total_challenges": len(CHALLENGES),
            },
        )

    @app.get(f"{route_path}/debug", response_class=HTMLResponse)
    def render_debug(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "debug.html",
            {
                "title": f"{settings.app_name} Debug Console",
                "mode": settings.app_mode,
                "route_path": route_path,
                "peer_path": peer_path,
                "student_path": route_path,
                "default_challenge_id": DEFAULT_CHALLENGE_ID,
                "challenges": public_challenges(),
                "flag_format": "ENPM604{...}",
            },
        )

    @app.post("/chat", response_model=ChatResponse)
    def chat(payload: ChatRequest) -> ChatResponse:
        return service.handle_chat(payload)

    @app.post("/query", response_model=ChatResponse)
    def query(payload: ChatRequest) -> ChatResponse:
        return service.handle_chat(payload)

    @app.post("/api/submit-flag", response_model=FlagSubmissionResponse)
    def submit_flag(payload: FlagSubmissionRequest) -> FlagSubmissionResponse:
        challenge = challenge_by_id(payload.challenge_id)
        correct = validate_flag(payload.challenge_id, payload.flag)
        next_challenge = CHALLENGES[challenge.level] if correct and challenge.level < len(CHALLENGES) else None
        message = (
            f"Correct. {challenge.owasp_id} {challenge.owasp_name} cleared."
            if correct
            else "Incorrect flag. Keep probing the vulnerable workflow."
        )
        return FlagSubmissionResponse(
            challenge_id=challenge.id,
            correct=correct,
            message=message,
            challenge_level=challenge.level,
            total_count=len(CHALLENGES),
            next_challenge_id=next_challenge.id if next_challenge else None,
        )

    @app.get("/api/challenges")
    def list_challenges() -> dict[str, object]:
        return {
            "default_challenge_id": DEFAULT_CHALLENGE_ID,
            "flag_format": "ENPM604{...}",
            "challenges": public_challenges(),
        }

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": settings.app_mode}

    return app

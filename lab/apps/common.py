from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from lab.shared.challenges import CHALLENGES
from lab.shared.config import Settings
from lab.shared.database import initialize_lab_state
from lab.shared.schemas import ChatRequest, ChatResponse


def create_lab_app(settings: Settings, route_path: str, service: object) -> FastAPI:
    app = FastAPI(title=settings.app_name)
    templates = Jinja2Templates(directory=str(settings.base_dir / "lab" / "templates"))
    static_dir = settings.base_dir / "lab" / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

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
            "index.html",
            {
                "mode": settings.app_mode,
                "title": settings.app_name,
                "route_path": route_path,
                "challenges": CHALLENGES,
            },
        )

    @app.post("/chat", response_model=ChatResponse)
    def chat(payload: ChatRequest) -> ChatResponse:
        return service.handle_chat(payload)

    @app.post("/query", response_model=ChatResponse)
    def query(payload: ChatRequest) -> ChatResponse:
        return service.handle_chat(payload)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": settings.app_mode}

    return app

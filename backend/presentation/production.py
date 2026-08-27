from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.presentation.api import api as financial_api


def create_production_app(frontend_dir: Path | None = None) -> FastAPI:
    """Hospeda API e SPA no mesmo domínio, simplificando cookies, OAuth e CORS."""
    root = frontend_dir or Path(__file__).resolve().parents[2] / "frontend" / "dist"
    app = FastAPI(title="GiControl")
    app.mount("/api", financial_api)
    if root.exists():
        assets = root / "assets"
        if assets.exists(): app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            candidate = (root / path).resolve()
            if path and candidate.is_relative_to(root.resolve()) and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(root / "index.html")
    return app


app = create_production_app()

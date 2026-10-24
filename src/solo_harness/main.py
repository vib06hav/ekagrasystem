from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles

from solo_harness import __version__
from solo_harness.bootstrap import bootstrap
from solo_harness.config import get_settings


def create_app(execution=None) -> FastAPI:
    state = {"ready": False, "error": None, "catalog": None}
    settings = get_settings()
    from solo_harness.web import ParticipantApplication, participant_router
    participant_application = ParticipantApplication(None, settings, execution=execution)
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            state["catalog"] = bootstrap(get_settings())
            participant_application.execution.runtime.catalog = state["catalog"]
            await participant_application.recover_persisted_operations()
            state["ready"] = True
        except Exception as exc:
            state["error"] = str(exc)
            raise
        yield
        state["ready"] = False
    app = FastAPI(title="SOLO Harness", version=__version__, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
    @app.get("/health/live")
    async def live(): return {"status": "live"}
    @app.get("/health/ready")
    async def ready(response: Response):
        if not state["ready"]:
            response.status_code = 503
            return {"status": "not_ready"}
        return {"status": "ready"}
    @app.get("/version")
    async def version(): return {"version": __version__, "build_id": get_settings().app_build_id}
    app.include_router(participant_router(participant_application))
    return app

app = create_app()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from scaler_script_pipeline.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Scaler Class Script Authoring Pipeline",
        version="0.1.0",
        description="Outline-first backend for generating, evaluating, reviewing, and signing off class scripts.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()

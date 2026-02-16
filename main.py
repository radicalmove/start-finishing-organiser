from fastapi import FastAPI
from fastapi.responses import JSONResponse

startup_error: str | None = None
try:
    from app import create_app

    app = create_app()
except Exception as exc:
    startup_error = f"{type(exc).__name__}: {exc}"
    app = FastAPI(title="Start Finishing Organiser")
    app.state.startup_error = startup_error


@app.get("/healthz")
def health():
    error = getattr(app.state, "startup_error", None) or startup_error
    if error:
        return JSONResponse({"status": "error", "detail": error}, status_code=503)
    return {"status": "ok"}


if startup_error:
    @app.get("/")
    def startup_failed():
        return JSONResponse(
            {
                "status": "error",
                "detail": startup_error,
                "hint": "Fix startup configuration, then restart SFO.",
            },
            status_code=503,
        )

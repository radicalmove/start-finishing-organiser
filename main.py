from app import create_app

app = create_app()


@app.get("/healthz")
def health():
    return {"status": "ok"}

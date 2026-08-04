from fastapi import FastAPI

app = FastAPI(title="MacroPulse", version="0.1.0")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "data_mode": "starter-no-live-data"}

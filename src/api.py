from fastapi import FastAPI, HTTPException
from src.schemas import MumzLensRequest, MumzLensResponse
from src.synthesizer import synthesize

app = FastAPI(
    title="MumzLens API",
    description="Stage-aware review intelligence for Mumzworld products.",
    version="1.0.0",
)


@app.get("/")
def root():
    return {"status": "ok", "service": "MumzLens"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/verdict", response_model=MumzLensResponse)
def get_verdict(request: MumzLensRequest):
    """
    Given a product name, a mother's life stage, and a list of reviews,
    returns a stage-filtered bilingual verdict with confidence score.
    """
    if not request.reviews:
        raise HTTPException(status_code=422, detail="Reviews list cannot be empty.")

    result = synthesize(request)
    return result
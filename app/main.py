from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.orchestrator import answer_question
from app.schemas import QueryRequest, QueryResponse


app = FastAPI()


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
	return QueryResponse(**answer_question(request.question))


@app.get("/health")
def health() -> dict[str, str]:
	return {"status": "ok"}


static_dir = Path(__file__).parent / "static"
if static_dir.is_dir() and any(static_dir.iterdir()):
	app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")

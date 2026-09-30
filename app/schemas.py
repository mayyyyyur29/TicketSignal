from pydantic import BaseModel


class QueryRequest(BaseModel):
	question: str


class QueryResponse(BaseModel):
	intent: str
	sql: str | None = None
	rows: list[dict] | None = None
	anomalies: list[dict] | None = None
	assumptions: list[str] | None = None
	error: str | None = None
	message: str | None = None

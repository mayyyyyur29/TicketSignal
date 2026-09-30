from fastapi.testclient import TestClient

from app import main


def test_health() -> None:
    assert TestClient(main.app).get("/health").json() == {"status": "ok"}


def test_query_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "answer_question",
        lambda question: {"intent": "data_query", "sql": "SELECT 1", "rows": [{"result": 1}]},
    )

    response = TestClient(main.app).post("/query", json={"question": "Count tickets"})

    assert response.status_code == 200
    assert response.json()["intent"] == "data_query"
    assert response.json()["rows"] == [{"result": 1}]
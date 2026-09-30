from app.llm.prompts import build_messages


def test_prompt_requests_structured_intents_and_anomaly_timeframe() -> None:
    messages = build_messages("Any anomalies this week?")

    assert messages[0]["role"] == "system"
    assert '"intent": "anomaly_query", "timeframe": "week"' in messages[0]["content"]
    assert messages[1] == {"role": "user", "content": "Any anomalies this week?"}


def test_prompt_distinguishes_late_resolution_from_stale_unresolved_ticket() -> None:
    system_prompt = build_messages("Which tickets missed 24 hours?")[0]["content"]

    assert "resolved tickets have resolution_time_hrs > N" in system_prompt
    assert "unresolved tickets have age_hours > N" in system_prompt
    assert "resolution_time_hrs > 24 OR status != 'Resolved'" not in system_prompt
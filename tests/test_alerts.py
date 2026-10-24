from services.dashboard.app.notify import _match, DEFAULT_RULES
def test_rule_match():
    ev = {"event_type": "anomaly.flagged", "payload": {"score": 0.8}}
    assert _match(DEFAULT_RULES[0], ev)
    ev["payload"]["score"] = 0.5
    assert not _match(DEFAULT_RULES[0], ev)

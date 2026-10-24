from services.compliance.app.norms import evaluate, classify

def test_classifier():
    assert classify(100, 120, False) == "ADVISORY_PASS"
    assert classify(100, 80, False) == "LIKELY_GAP"
    assert classify(100, 20, False) == "RECOMMEND_INSPECT"
    assert classify(100, None, False) == "INSUFFICIENT_EVIDENCE"

def test_evaluate():
    f = evaluate("computer_science_120_seats", {"computer_workstation": {"count": 45, "max_conf": .9}},
                 {"rooms": {"computer lab": {"area_sqm": 80.0}}}, {"library_books": "2500"})
    by = {x["norm_key"]: x for x in f}
    assert by["computer_workstations_min"]["finding"] == "ADVISORY_PASS"
    assert by["computer_lab_min_area_sqm"]["finding"] == "ADVISORY_PASS"
    assert by["library_min_books"]["finding"] == "ADVISORY_PASS"
    assert all("Advisory" in x["advisory_disclaimer"] for x in f)

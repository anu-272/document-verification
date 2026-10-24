from datetime import date, timedelta
from services.validation.app.engine import run_validation, load_checklist

def doc(t, **f): return {"id": f"id-{t}", "doc_type": t, "extracted_json": {"fields": f}, "ocr_confidence": 0.9}

def test_missing_and_expired():
    docs = [doc("STATE_NOC", valid_until="2020-01-01", institute_id="1-1"),
            doc("AFFIDAVIT", institute_id="1-12345678")]
    rec = {"institute_id": "1-12345678", "faculty_count": 42}
    rep = run_validation("EOA", docs, rec)
    by = {r["rule_id"]: r for r in rep["results"]}
    assert by["FIRE_NOC_REQUIRED"]["status"] == "FAILED"
    assert by["STATE_NOC_EXPIRY"]["status"] == "FAILED" and "expired" in by["STATE_NOC_EXPIRY"]["message"]
    assert by["INSTITUTE_ID_CONSISTENT"]["status"] == "FAILED"   # 1-1 vs 1-12345678
    assert rep["summary"]["status"] == "DEFICIENT"

def test_all_pass():
    fut = (date.today() + timedelta(days=400)).isoformat()
    docs = [doc("FIRE_SAFETY_NOC", valid_until=fut), doc("STATE_NOC", valid_until=fut, institute_id="1-9"),
            doc("AFFIDAVIT", institute_id="1-9"), doc("TER_PAYMENT_RECEIPT"), doc("NAAC_CERTIFICATE", valid_until=fut, institute_id="1-9")]
    rep = run_validation("EOA", docs, {"institute_id": "1-9", "faculty_count": 30})
    assert rep["summary"]["mandatory_failed"] == 0

def test_checklists_load():
    for c in ("EOA", "NEW_PROGRAMME", "INTAKE_INCREASE"):
        assert load_checklist(c)["rules"]

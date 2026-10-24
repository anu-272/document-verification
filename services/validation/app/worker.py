"""Consumes document.processed; re-validates the whole application each time."""
import json
from shared import events
from shared.db import conn
from shared.gemini import explain
from .engine import run_validation
from .records import get_record

def handle(ev):
    app_id = ev["aggregate_id"]
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT id,doc_type,extracted_json,ocr_confidence FROM documents "
                    "WHERE application_id=%s AND status='PROCESSED'", (app_id,))
        docs = cur.fetchall()
    record = get_record(app_id)
    report = run_validation(record.get("category", "EOA"), docs, record)
    with conn() as c:
        cur = c.cursor()
        cur.execute("DELETE FROM validation_results WHERE application_id=%s", (app_id,))
        for r in report["results"]:
            plain = r["message"]
            if r["status"] == "FAILED":
                plain = explain(f"Rewrite this regulatory deficiency in plain English for an institution "
                                f"administrator in one sentence: {r['message']}", r["message"])
            cur.execute("""INSERT INTO validation_results(application_id,rule_id,status,severity,message,plain_message,evidence)
                           VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                        (app_id, r["rule_id"], r["status"], r["severity"], r["message"], plain, json.dumps(r["evidence"])))
    events.publish(events.VALIDATION_COMPLETED, app_id, report["summary"] | {"checklist": report["checklist_version"]},
                   actor="validation-engine")

if __name__ == "__main__":
    events.consume("validation", "v1", {events.DOCUMENT_PROCESSED}, handle)

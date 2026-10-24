from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from shared import events
from shared.db import conn

app = FastAPI(title="Anomaly Service")

class Review(BaseModel):
    reviewer: str
    outcome: str  # CONFIRMED_CONCERN | FALSE_POSITIVE | NEEDS_MORE_EVIDENCE

@app.get("/api/v1/anomalies")
def queue(only_open: bool = True):
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM anomaly_flags " + ("WHERE reviewed_by_human=false " if only_open else "") +
                    "ORDER BY confidence_score DESC LIMIT 200")
        return cur.fetchall()

@app.get("/api/v1/documents/{doc_id}/anomalies")
def for_doc(doc_id: str):
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM anomaly_flags WHERE document_id=%s", (doc_id,))
        return cur.fetchall()

@app.post("/api/v1/anomalies/{flag_id}/review")
def review(flag_id: str, r: Review):
    if r.outcome not in {"CONFIRMED_CONCERN", "FALSE_POSITIVE", "NEEDS_MORE_EVIDENCE"}:
        raise HTTPException(422, "invalid outcome")
    with conn() as c:
        cur = c.cursor()
        cur.execute("UPDATE anomaly_flags SET reviewed_by_human=true,reviewer=%s,review_outcome=%s WHERE flag_id=%s RETURNING document_id",
                    (r.reviewer, r.outcome, flag_id))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "flag not found")
    events.publish("anomaly.reviewed", str(row["document_id"]), {"flag_id": flag_id, "outcome": r.outcome}, actor=r.reviewer)
    return {"ok": True}

@app.get("/health")
def health():
    return {"ok": True}

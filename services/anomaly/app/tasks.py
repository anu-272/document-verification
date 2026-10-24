"""Fan-out / scatter-gather: 5 checks in parallel Celery group, then aggregator chord callback."""
import json
from celery import Celery, group, chord
from shared import events
from shared.config import REDIS_URL, ANOMALY_THRESHOLD, ADVISORY_DISCLAIMER
from shared.db import conn
from shared.gemini import explain
from . import checks

celery = Celery("anomaly", broker=REDIS_URL, backend=REDIS_URL)
celery.conf.task_default_queue = "anomaly"

WEIGHTS = {"ELA_EDIT_DETECTED": 0.35, "METADATA_INCONSISTENT": 0.25, "FONT_MISMATCH": 0.15,
           "DUPLICATE_DOCUMENT": 0.20, "IDENTIFIER_MISMATCH": 0.05}

def _safe(fn, doc_id, flag):
    try:
        return fn(doc_id)
    except Exception as e:
        return {"score": 0.0, "flag_type": flag, "region": None, "reason": f"Check failed: {e}", "error": True}

@celery.task
def ela_analysis(doc_id): return _safe(checks.ela_analysis, doc_id, "ELA_EDIT_DETECTED")
@celery.task
def metadata_analysis(doc_id): return _safe(checks.metadata_analysis, doc_id, "METADATA_INCONSISTENT")
@celery.task
def font_analysis(doc_id): return _safe(checks.font_analysis, doc_id, "FONT_MISMATCH")
@celery.task
def duplicate_check(doc_id): return _safe(checks.duplicate_check, doc_id, "DUPLICATE_DOCUMENT")
@celery.task
def identifier_check(doc_id): return _safe(checks.identifier_check, doc_id, "IDENTIFIER_MISMATCH")

def fuse(results: list) -> float:
    """Weighted fusion; a very strong single signal (>=0.9) is never diluted below 0.5."""
    s = sum(WEIGHTS[r["flag_type"]] * r["score"] for r in results)
    strongest = max((r["score"] for r in results), default=0)
    return round(max(s, 0.5 if strongest >= 0.9 else 0.0), 3)

@celery.task
def aggregate_scores(results: list, doc_id: str, application_id: str):
    final = fuse(results)
    flagged = [r for r in results if r["score"] >= 0.3 and not r.get("error")]
    if final <= ANOMALY_THRESHOLD or not flagged:
        events.publish(events.ANOMALY_CLEARED, application_id, {"document_id": doc_id, "score": final}, actor="anomaly-detector")
        return {"flagged": False, "score": final}
    top = max(flagged, key=lambda r: r["score"] * WEIGHTS[r["flag_type"]])
    breakdown = ", ".join(f"{r['flag_type']}={r['score']:.2f}" for r in results)
    expl = explain(
        "In 2 sentences, for an AICTE officer, explain why this document was flagged as a possible "
        f"anomaly. State clearly this is only a preliminary indicator. Findings: {breakdown}. "
        f"Main reason: {top['reason']}",
        f"{top['reason']}. This is a preliminary indicator; human verification is required.")
    with conn() as c:
        cur = c.cursor()
        cur.execute("""INSERT INTO anomaly_flags(document_id,flag_type,confidence_score,region,reason,
                       gemini_explanation,advisory_disclaimer) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING flag_id""",
                    (doc_id, top["flag_type"], final, json.dumps(top["region"]),
                     top["reason"], expl, ADVISORY_DISCLAIMER))
        flag_id = str(cur.fetchone()["flag_id"])
    events.publish(events.ANOMALY_FLAGGED, application_id,
                   {"flag_id": flag_id, "document_id": doc_id, "flag_type": top["flag_type"],
                    "score": final, "breakdown": results}, actor="anomaly-detector")
    return {"flagged": True, "score": final, "flag_id": flag_id}

def run_for_document(doc_id: str, application_id: str):
    header = group(ela_analysis.s(doc_id), metadata_analysis.s(doc_id), font_analysis.s(doc_id),
                   duplicate_check.s(doc_id), identifier_check.s(doc_id))
    return chord(header)(aggregate_scores.s(doc_id, application_id))

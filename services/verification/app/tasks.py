"""State machine: PENDING -> QUERYING -> {VERIFIED | MISMATCH | EXPIRED | SOURCE_UNAVAILABLE -> retry -> MANUAL_REVIEW}.
Exponential backoff 1s,2s,4s (max 3 retries); a Celery beat task re-queues stale PENDING rows."""
import json
from celery import Celery
from shared import events
from shared.config import REDIS_URL
from shared.db import conn
from .adapters import adapter_for
from .base import VStatus, SourceUnavailable, VerificationResult
from . import circuit

celery = Celery("verification", broker=REDIS_URL, backend=REDIS_URL)
celery.conf.task_default_queue = "verification"
celery.conf.beat_schedule = {"retry-pending": {"task": "services.verification.app.tasks.retry_pending", "schedule": 300.0}}

def _record(doc_id, res: VerificationResult, attempts):
    with conn() as c:
        cur = c.cursor()
        cur.execute("""INSERT INTO verification_results(document_id,source,status,query_params,source_response,evidence_hash,attempts)
                       VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (doc_id, res.source, res.status.value, json.dumps(res.query_params),
                     json.dumps({"response": res.source_response, "discrepancies": res.discrepancies}, default=str),
                     res.evidence_hash, attempts))

@celery.task(bind=True, max_retries=3)
def verify_document(self, doc_id: str, application_id: str):
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT doc_type,extracted_json FROM documents WHERE id=%s", (doc_id,))
        d = cur.fetchone()
    ad = adapter_for(d["doc_type"])
    if not ad:
        res = VerificationResult(VStatus.MANUAL_REVIEW, "NONE", {}, {"reason": "No issuing-authority adapter for this document type"})
        _record(doc_id, res, 0)
        events.publish(events.VERIFICATION_COMPLETED, application_id, {"document_id": doc_id, "status": res.status.value}, "verifier")
        return
    events.publish("verification.querying", application_id, {"document_id": doc_id, "source": ad.get_source_name()}, "verifier")
    try:
        res = circuit.call(ad.SOURCE, ad.verify, d["extracted_json"] or {})
    except SourceUnavailable as e:
        if self.request.retries < self.max_retries:
            _record(doc_id, VerificationResult(VStatus.SOURCE_UNAVAILABLE, ad.SOURCE, {}, {"error": str(e)}), self.request.retries + 1)
            raise self.retry(exc=e, countdown=2 ** self.request.retries)  # 1s, 2s, 4s
        res = VerificationResult(VStatus.MANUAL_REVIEW, ad.SOURCE, {}, {"error": str(e), "note": "max retries exceeded"})
    _record(doc_id, res, self.request.retries + 1)
    events.publish(events.VERIFICATION_COMPLETED, application_id,
                   {"document_id": doc_id, "source": res.source, "status": res.status.value,
                    "evidence_hash": res.evidence_hash, "discrepancies": res.discrepancies}, "verifier")

@celery.task
def retry_pending():
    """Beat task: re-queue docs whose latest verification is SOURCE_UNAVAILABLE."""
    with conn() as c:
        cur = c.cursor()
        cur.execute("""SELECT DISTINCT ON (v.document_id) v.document_id, d.application_id, v.status
                       FROM verification_results v JOIN documents d ON d.id=v.document_id
                       ORDER BY v.document_id, v.checked_at DESC""")
        rows = [r for r in cur.fetchall() if r["status"] == VStatus.SOURCE_UNAVAILABLE.value]
    for r in rows:
        verify_document.delay(str(r["document_id"]), r["application_id"])
    return len(rows)

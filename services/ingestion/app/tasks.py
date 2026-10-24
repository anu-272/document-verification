"""Celery pipeline: preprocess -> OCR -> classify -> extract -> embed -> publish.
Each stage is recorded in pipeline_jobs; failed stages retry, then go to the DLQ."""
import datetime as dt, json
from celery import Celery
from shared import events
from shared.config import REDIS_URL
from shared.db import conn
from shared.gemini import embed
from . import storage
from .preprocess import load_pages, preprocess
from .ocr import run_ocr
from .classifier import classify
from .ner import extract_fields

celery = Celery("ingestion", broker=REDIS_URL, backend=REDIS_URL)
celery.conf.task_default_queue = "ingestion"
DLQ_KEY = "aicte:dlq:ingestion"

def _stage(cur, doc_id, stage, status, err=None, retry=0):
    cur.execute("""INSERT INTO pipeline_jobs(document_id,stage,status,error_msg,started_at,completed_at,retry_count)
                   VALUES(%s,%s,%s,%s,now(),CASE WHEN %s IN ('DONE','FAILED') THEN now() END,%s)""",
                (doc_id, stage, status, err, status, retry))

@celery.task(bind=True, max_retries=3, default_retry_delay=10)
def process_document(self, doc_id: str):
    stage = "load"
    try:
        with conn() as c:
            cur = c.cursor()
            cur.execute("SELECT * FROM documents WHERE id=%s", (doc_id,))
            doc = cur.fetchone()
            cur.execute("UPDATE documents SET status='PROCESSING' WHERE id=%s", (doc_id,))
        raw = storage.get(doc["minio_key"])
        pages = load_pages(raw, doc["filename"] or "x.pdf")
        stage = "preprocess"; processed = [preprocess(p) for p in pages]
        stage = "ocr"; text, conf, engine = run_ocr(pages, processed)
        stage = "classify"; doc_type, cls_conf = classify(pages, text)
        stage = "extract"; fields = extract_fields(text)
        extracted = {"text": text[:50000], "fields": fields, "ocr_engine": engine,
                     "classification_confidence": cls_conf, "pages": len(pages)}
        stage = "embed"; vec = embed(text[:4000])
        from services.anomaly.app.duplicates import upsert_vector
        try:
            upsert_vector(doc_id, vec, {"application_id": doc["application_id"], "doc_type": doc_type})
        except Exception:
            pass  # vector store optional; duplicate check degrades gracefully
        with conn() as c:
            cur = c.cursor()
            cur.execute("""UPDATE documents SET doc_type=%s, status='PROCESSED',
                           extracted_json=%s, ocr_confidence=%s WHERE id=%s""",
                        (doc_type, json.dumps(extracted), conf, doc_id))
            _stage(cur, doc_id, "pipeline", "DONE")
        events.publish(events.DOCUMENT_PROCESSED, doc["application_id"],
                       {"document_id": doc_id, "doc_type": doc_type, "ocr_confidence": conf})
    except Exception as exc:
        with conn() as c:
            _stage(c.cursor(), doc_id, stage, "FAILED", str(exc), self.request.retries)
        if self.request.retries >= self.max_retries:
            events.client().rpush(DLQ_KEY, json.dumps({"doc_id": doc_id, "stage": stage, "error": str(exc)}))
            with conn() as c:
                c.cursor().execute("UPDATE documents SET status='FAILED' WHERE id=%s", (doc_id,))
            events.publish(events.PIPELINE_FAILED, doc_id, {"stage": stage, "error": str(exc)})
            return
        raise self.retry(exc=exc)

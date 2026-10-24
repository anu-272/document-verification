import hashlib, uuid
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from shared import events
from shared.db import conn
from . import storage
from .tasks import process_document

app = FastAPI(title="Ingestion Service")
ALLOWED = (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff")
MAX_BYTES = 25 * 1024 * 1024

@app.post("/api/v1/documents/upload")
async def upload(application_id: str = Form(...), files: List[UploadFile] = File(...)):
    jobs = []
    for f in files:
        if not f.filename.lower().endswith(ALLOWED):
            raise HTTPException(415, f"Unsupported file type: {f.filename}")
        data = await f.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(413, f"{f.filename} exceeds 25MB")
        doc_id = str(uuid.uuid4())
        key = f"{application_id}/{doc_id}/{f.filename}"
        storage.put(key, data)
        with conn() as c:
            c.cursor().execute(
                "INSERT INTO documents(id,application_id,minio_key,filename,content_sha256) VALUES(%s,%s,%s,%s,%s)",
                (doc_id, application_id, key, f.filename, hashlib.sha256(data).hexdigest()))
        events.publish(events.DOCUMENT_UPLOADED, application_id,
                       {"document_id": doc_id, "filename": f.filename})
        process_document.delay(doc_id)
        jobs.append({"job_id": doc_id, "filename": f.filename, "status": "QUEUED"})
    return {"jobs": jobs}

@app.get("/api/v1/documents/{job_id}")
def status(job_id: str):
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT id,status,doc_type,ocr_confidence FROM documents WHERE id=%s", (job_id,))
        d = cur.fetchone()
        if not d:
            raise HTTPException(404, "Not found")
        cur.execute("SELECT stage,status,error_msg,retry_count FROM pipeline_jobs WHERE document_id=%s ORDER BY started_at", (job_id,))
        d["stages"] = cur.fetchall()
    return d

@app.get("/api/v1/documents/{doc_id}/extracted")
def extracted(doc_id: str):
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT id,application_id,doc_type,extracted_json,ocr_confidence FROM documents WHERE id=%s", (doc_id,))
        d = cur.fetchone()
    if not d:
        raise HTTPException(404, "Not found")
    return d

@app.get("/health")
def health():
    return {"ok": True}

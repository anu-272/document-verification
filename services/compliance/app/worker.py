"""On document.processed for evidence docs (photos/floor plans/certs), re-evaluates the application."""
import json, os, tempfile
import cv2, numpy as np
from shared import events
from shared.db import conn
from services.ingestion.app import storage
from services.ingestion.app.preprocess import load_pages
from . import vision, floorplan, norms

PHOTO_EXT = (".jpg", ".jpeg", ".png")
VIDEO_EXT = (".mp4", ".mov", ".avi")
EVIDENCE_TYPES = {"BUILDING_PLAN", "INFRASTRUCTURE_PHOTO", "LIBRARY_CERTIFICATE", "UNKNOWN"}

def handle(ev):
    app_id = ev["aggregate_id"]
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT id,doc_type,filename,minio_key,extracted_json FROM documents WHERE application_id=%s AND status='PROCESSED'", (app_id,))
        docs = cur.fetchall()
    programme = os.getenv("DEFAULT_NORM_SET", "computer_science_120_seats")  # TODO: derive from application record
    images, plan, certs = [], {"rooms": {}}, {}
    for d in docs:
        fn = (d["filename"] or "").lower()
        fields = (d["extracted_json"] or {}).get("fields", {})
        certs.update({k: v for k, v in fields.items()})
        if d["doc_type"] == "BUILDING_PLAN":
            pages = load_pages(storage.get(d["minio_key"]), fn)
            res = floorplan.process(pages[0])
            plan["rooms"].update(res["rooms"])
        elif fn.endswith(VIDEO_EXT):
            with tempfile.NamedTemporaryFile(suffix=os.path.splitext(fn)[1]) as t:
                t.write(storage.get(d["minio_key"])); t.flush()
                images += list(vision.sample_frames(t.name))
        elif fn.endswith(PHOTO_EXT) and d["doc_type"] in ("INFRASTRUCTURE_PHOTO", "UNKNOWN"):
            images.append(cv2.imdecode(np.frombuffer(storage.get(d["minio_key"]), np.uint8), 1))
    det = vision.detect(images) if images else {}
    findings = norms.evaluate(programme, det, plan, certs)
    with conn() as c:
        cur = c.cursor()
        cur.execute("DELETE FROM compliance_findings WHERE application_id=%s", (app_id,))
        for f in findings:
            cur.execute("""INSERT INTO compliance_findings(application_id,norm_key,required,observed,finding,evidence,advisory_disclaimer)
                           VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                        (app_id, f["norm_key"], f["required"], f["observed"], f["finding"],
                         json.dumps(f["evidence"]), f["advisory_disclaimer"]))
    summary = {t: sum(1 for f in findings if f["finding"] == t) for t in
               ("ADVISORY_PASS", "INSUFFICIENT_EVIDENCE", "LIKELY_GAP", "RECOMMEND_INSPECT")}
    events.publish(events.COMPLIANCE_COMPLETED, app_id, summary, actor="compliance-assistant")

if __name__ == "__main__":
    events.consume("compliance", "c1", {events.DOCUMENT_PROCESSED}, handle)

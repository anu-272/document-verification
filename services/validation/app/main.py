from fastapi import FastAPI
from shared.db import conn
from .engine import load_checklist

app = FastAPI(title="Validation Service")

@app.get("/api/v1/validation/{application_id}")
def report(application_id: str):
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT rule_id,status,severity,message,plain_message,evidence FROM validation_results WHERE application_id=%s", (application_id,))
        return {"application_id": application_id, "results": cur.fetchall()}

@app.get("/api/v1/checklists/{category}")
def checklist(category: str):
    return load_checklist(category.upper())

@app.get("/health")
def health():
    return {"ok": True}

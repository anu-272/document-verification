from fastapi import FastAPI
from shared.db import conn

app = FastAPI(title="Compliance Service")

@app.get("/api/v1/compliance/{application_id}")
def findings(application_id: str):
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM compliance_findings WHERE application_id=%s ORDER BY norm_key", (application_id,))
        return {"disclaimer": "Advisory only; physical inspection and final decisions rest with AICTE.",
                "findings": cur.fetchall()}

@app.get("/health")
def health():
    return {"ok": True}

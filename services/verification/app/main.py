from fastapi import FastAPI
from shared.db import conn
from .circuit import BREAKERS
from .adapters import ADAPTERS

app = FastAPI(title="Verification Service")

@app.get("/api/v1/verification/{application_id}")
def by_app(application_id: str):
    with conn() as c:
        cur = c.cursor()
        cur.execute("""SELECT DISTINCT ON (v.document_id) v.*, d.doc_type FROM verification_results v
                       JOIN documents d ON d.id=v.document_id WHERE d.application_id=%s
                       ORDER BY v.document_id, v.checked_at DESC""", (application_id,))
        return cur.fetchall()

@app.get("/api/v1/integrations/status")
def integrations():
    return [{"source": n, "doc_types": sorted(a.DOC_TYPES), "circuit": BREAKERS[n].current_state} for n, a in ADAPTERS.items()]

@app.get("/health")
def health():
    return {"ok": True}

import asyncio, json
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as aioredis
from shared.config import REDIS_URL
from shared.db import conn
from shared import events
from . import auth

app = FastAPI(title="Dashboard Service (CQRS read side)")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])

class Login(BaseModel):
    username: str
    password: str

@app.post("/api/v1/auth/login")
def login(b: Login):
    with conn() as c:
        cur = c.cursor(); cur.execute("SELECT * FROM users WHERE username=%s", (b.username,)); u = cur.fetchone()
    if not u or not auth.verify_pw(b.password, u["password_hash"]):
        raise HTTPException(401, "Bad credentials")
    return {"token": auth.make_token(u["username"], u["role"]), "role": u["role"]}

def _q(sql, *args):
    with conn() as c:
        cur = c.cursor(); cur.execute(sql, args); return cur.fetchall()

@app.get("/api/v1/dashboard/applications")
def applications(u=Depends(auth.require("OFFICER", "ADMIN", "INSTITUTION"))):
    rows = _q("""SELECT a.application_id, a.documents, a.processed,
                 coalesce((SELECT sum(failed) FROM mv_deficiency_summary d WHERE d.application_id=a.application_id),0) AS deficiencies,
                 coalesce((SELECT count(*) FROM mv_anomaly_queue q WHERE q.application_id=a.application_id),0) AS open_anomalies
                 FROM mv_application_status a ORDER BY a.application_id""")
    if u["role"] == "INSTITUTION":  # institutions only see applications they own
        rows = [r for r in rows if r["application_id"] in _owned(u["sub"])]
    return rows

def _owned(username):  # simple convention: username 'inst-APP-1001' owns APP-1001
    return {username.replace("inst-", "")}

@app.get("/api/v1/dashboard/applications/{app_id}")
def application(app_id: str, u=Depends(auth.require("OFFICER", "ADMIN", "INSTITUTION"))):
    if u["role"] == "INSTITUTION" and app_id not in _owned(u["sub"]):
        raise HTTPException(403, "Not your application")
    return {
        "documents": _q("SELECT id,doc_type,status,ocr_confidence,filename FROM documents WHERE application_id=%s", app_id),
        "validation": _q("SELECT rule_id,status,severity,plain_message,evidence FROM validation_results WHERE application_id=%s", app_id),
        "verification": _q("""SELECT DISTINCT ON (v.document_id) v.document_id,v.source,v.status,v.evidence_hash,v.checked_at
                             FROM verification_results v JOIN documents d ON d.id=v.document_id WHERE d.application_id=%s
                             ORDER BY v.document_id, v.checked_at DESC""", app_id),
        "anomalies": _q("""SELECT f.* FROM anomaly_flags f JOIN documents d ON d.id=f.document_id WHERE d.application_id=%s""", app_id),
        "compliance": _q("SELECT norm_key,required,observed,finding,advisory_disclaimer FROM compliance_findings WHERE application_id=%s", app_id),
    }

@app.get("/api/v1/dashboard/applications/{app_id}/audit")
def audit(app_id: str, u=Depends(auth.require("OFFICER", "ADMIN"))):
    return _q("SELECT id,event_type,actor,payload,occurred_at FROM event_store WHERE aggregate_id=%s ORDER BY id", app_id)

@app.get("/api/v1/dashboard/anomaly-queue")
def anomaly_queue(u=Depends(auth.require("OFFICER", "ADMIN"))):
    return _q("SELECT * FROM mv_anomaly_queue")

@app.get("/api/v1/dashboard/summary")
def summary(u=Depends(auth.require("OFFICER", "ADMIN"))):
    return {"verification": _q("SELECT status, sum(n) AS n FROM mv_verification_status GROUP BY status"),
            "deficiencies": _q("SELECT severity, sum(failed) AS n FROM mv_deficiency_summary GROUP BY severity"),
            "open_anomalies": _q("SELECT count(*) AS n FROM mv_anomaly_queue")[0]["n"]}

@app.get("/api/v1/notifications")
def notifications(u=Depends(auth.current_user)):
    return [json.loads(x) for x in events.client().lrange(f"aicte:inbox:{u['role']}", 0, 49)]

@app.get("/api/v1/admin/rules/{category}")
def rules(category: str, u=Depends(auth.require("ADMIN"))):
    from services.validation.app.engine import load_checklist
    return load_checklist(category.upper())

@app.websocket("/ws")
async def ws(websocket: WebSocket, token: str = Query(...)):
    try:
        user = auth.jwt.decode(token, auth.JWT_SECRET, algorithms=["HS256"])
    except Exception:
        await websocket.close(code=4401); return
    if user["role"] == "INSTITUTION":
        await websocket.close(code=4403); return
    await websocket.accept()
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    ps = r.pubsub(); await ps.subscribe("aicte.live")
    try:
        while True:
            m = await ps.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if m:
                await websocket.send_text(m["data"])
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass
    finally:
        await ps.close(); await r.close()

@app.get("/health")
def health():
    return {"ok": True}

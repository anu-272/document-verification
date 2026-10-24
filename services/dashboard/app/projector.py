"""Write side: consumes EVERY event from the bus and appends it to the immutable event_store.
Also refreshes materialized views and fires notification rules."""
import json, threading, time
from shared import events
from shared.db import conn
from .notify import evaluate_alerts

_last_refresh = 0.0
VIEWS = ["mv_application_status", "mv_deficiency_summary", "mv_verification_status", "mv_anomaly_queue"]

def refresh_views(force=False):
    global _last_refresh
    if not force and time.time() - _last_refresh < 3:  # coalesce bursts; periodic 30s loop also runs
        return
    with conn() as c:
        cur = c.cursor()
        for v in VIEWS:
            cur.execute(f"REFRESH MATERIALIZED VIEW {v}")
    _last_refresh = time.time()

def handle(ev):
    with conn() as c:
        c.cursor().execute("""INSERT INTO event_store(event_id,event_type,aggregate_id,payload,actor,occurred_at)
                              VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT (event_id) DO NOTHING""",
                           (ev["event_id"], ev["event_type"], ev["aggregate_id"], json.dumps(ev["payload"]),
                            ev["actor"], ev["occurred_at"]))
    refresh_views()
    events.client().publish("aicte.live", json.dumps(ev))  # fan-out to WebSocket servers
    evaluate_alerts(ev)

def periodic_refresh():
    while True:
        time.sleep(30)
        try: refresh_views(force=True)
        except Exception as e: print("refresh failed", e)

if __name__ == "__main__":
    threading.Thread(target=periodic_refresh, daemon=True).start()
    ALL = {events.DOCUMENT_UPLOADED, events.DOCUMENT_PROCESSED, events.VALIDATION_COMPLETED, events.ANOMALY_FLAGGED,
           events.ANOMALY_CLEARED, events.VERIFICATION_COMPLETED, events.COMPLIANCE_COMPLETED, events.PIPELINE_FAILED,
           "verification.querying", "anomaly.reviewed"}
    events.consume("dashboard", "d1", ALL, handle)

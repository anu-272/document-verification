"""Event bus on Redis Streams. Modules never call each other directly;
they publish events and consume them via consumer groups."""
import json, uuid, datetime as dt
import redis
from shared.config import REDIS_URL

STREAM = "aicte.events"

# Event types
DOCUMENT_UPLOADED = "document.uploaded"
DOCUMENT_PROCESSED = "document.processed"      # Module 1 -> 2,3,4,5
VALIDATION_COMPLETED = "validation.completed"  # Module 2
ANOMALY_FLAGGED = "anomaly.flagged"            # Module 3
ANOMALY_CLEARED = "anomaly.cleared"
VERIFICATION_COMPLETED = "verification.completed"  # Module 4
COMPLIANCE_COMPLETED = "compliance.completed"  # Module 5
PIPELINE_FAILED = "pipeline.failed"

_r = None
def client():
    global _r
    if _r is None:
        _r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    return _r

def publish(event_type: str, aggregate_id: str, payload: dict, actor: str = "system") -> str:
    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "aggregate_id": aggregate_id,
        "actor": actor,
        "occurred_at": dt.datetime.utcnow().isoformat() + "Z",
        "payload": json.dumps(payload, default=str),
    }
    client().xadd(STREAM, event, maxlen=100000)
    return event["event_id"]

def consume(group: str, consumer: str, event_types: set, handler, block_ms=5000):
    """Blocking consumer loop. handler(event_dict) -> None. Acks on success."""
    r = client()
    try:
        r.xgroup_create(STREAM, group, id="0", mkstream=True)
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
    while True:
        resp = r.xreadgroup(group, consumer, {STREAM: ">"}, count=10, block=block_ms)
        for _, msgs in resp or []:
            for msg_id, data in msgs:
                if data["event_type"] in event_types:
                    data["payload"] = json.loads(data["payload"])
                    try:
                        handler(data)
                    except Exception as exc:  # never lose events silently
                        publish(PIPELINE_FAILED, data["aggregate_id"],
                                {"group": group, "error": str(exc), "event": data["event_type"]})
                r.xack(STREAM, group, msg_id)

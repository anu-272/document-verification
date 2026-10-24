from shared import events
from .tasks import run_for_document

def handle(ev):
    run_for_document(ev["payload"]["document_id"], ev["aggregate_id"])

if __name__ == "__main__":
    events.consume("anomaly", "a1", {events.DOCUMENT_PROCESSED}, handle)

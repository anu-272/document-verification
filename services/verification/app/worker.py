from shared import events
from .tasks import verify_document

def handle(ev):
    verify_document.delay(ev["payload"]["document_id"], ev["aggregate_id"])

if __name__ == "__main__":
    events.consume("verification", "ver1", {events.DOCUMENT_PROCESSED}, handle)

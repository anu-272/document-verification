from services.ingestion.app.classifier import classify
from services.ingestion.app.ner import extract_fields

TXT = "Fire Service Department. No Objection Certificate for fire safety. Certificate No: FS/2025/0042. Issued on 12/03/2025. Valid up to 11/03/2027. Institute ID: 1-12345678"
def test_classify(): assert classify([], TXT)[0] == "FIRE_SAFETY_NOC"
def test_extract():
    f = extract_fields(TXT)
    assert f["valid_until"] == "2027-03-11" and f["certificate_number"] == "FS/2025/0042" and f["institute_id"] == "1-12345678"

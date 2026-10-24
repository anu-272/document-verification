"""Read-only client for AICTE institutional records. The validation engine never touches
the AICTE DB directly; it uses this controlled API layer. Set AICTE_RECORDS_URL for real
integration; otherwise a synthetic dataset is used (demo/evaluation)."""
import os, requests

URL = os.getenv("AICTE_RECORDS_URL", "")
TOKEN = os.getenv("AICTE_RECORDS_TOKEN", "")

SYNTHETIC = {
    "APP-1001": {"institute_id": "1-12345678", "institute_name": "Demo Institute of Technology",
                 "faculty_count": 42, "approved_intake": 240, "previous_eoa": "2025-26",
                 "deficiency_status": "NONE", "ter_paid": True, "category": "EOA"},
    "APP-1002": {"institute_id": "1-87654321", "institute_name": "Sample College of Engineering",
                 "faculty_count": 12, "approved_intake": 120, "previous_eoa": "2025-26",
                 "deficiency_status": "OPEN", "ter_paid": False, "category": "EOA"},
}

def get_record(application_id: str) -> dict:
    if URL:
        r = requests.get(f"{URL}/institutions/by-application/{application_id}",
                         headers={"Authorization": f"Bearer {TOKEN}"}, timeout=10)
        r.raise_for_status()
        return r.json()
    return SYNTHETIC.get(application_id, {})

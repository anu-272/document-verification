"""Adapters. Real mode calls the official endpoint (configure *_URL / *_KEY env vars and ensure
you are authorised to use it). Mock mode (default) returns synthetic deterministic data for demos.
No adapter bypasses access controls: if credentials/URL are absent, SOURCE_UNAVAILABLE is raised
and the case is routed to manual review."""
import os, hashlib, requests
from datetime import date
from shared.config import USE_MOCK_VERIFICATION
from .base import *

def _mock_record(doc: dict, source: str) -> dict:
    """Deterministic mock: certificate numbers ending in 'X' simulate mismatch, 'E' expired, 'U' source down."""
    f = doc.get("fields", {})
    num = str(f.get("certificate_number", ""))
    if num.endswith("U"):
        raise SourceUnavailable(f"{source} mock outage")
    rec = {"certificate_number": num, "institute_id": f.get("institute_id"),
           "valid_until": f.get("valid_until") or "2099-01-01", "source": source, "status": "ACTIVE"}
    if num.endswith("X"):
        rec["institute_id"] = "0-00000000"
    if num.endswith("E"):
        rec["valid_until"] = "2020-01-01"; rec["status"] = "EXPIRED"
    return rec

class _HttpAdapter(BaseVerificationAdapter):
    URL_ENV = ""; KEY_ENV = ""; COMPARE = ("certificate_number", "institute_id", "valid_until")

    def _fetch(self, doc: dict) -> dict:
        if USE_MOCK_VERIFICATION:
            return _mock_record(doc, self.SOURCE)
        url, key = os.getenv(self.URL_ENV), os.getenv(self.KEY_ENV)
        if not url or not key:
            raise SourceUnavailable(f"{self.SOURCE} not configured/authorised")
        try:
            r = requests.get(url, params={"certificate_number": doc["fields"].get("certificate_number")},
                             headers={"Authorization": f"Bearer {key}"}, timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            raise SourceUnavailable(str(e))

    def verify(self, doc):
        official = self._fetch(doc)
        qp = {"certificate_number": doc.get("fields", {}).get("certificate_number")}
        diffs = compare(doc.get("fields", {}), official, self.COMPARE)
        exp = official.get("valid_until")
        if official.get("status") == "EXPIRED" or (exp and exp < date.today().isoformat()):
            st = VStatus.EXPIRED
        elif diffs:
            st = VStatus.MISMATCH
        else:
            st = VStatus.VERIFIED
        return VerificationResult(st, self.SOURCE, qp, official, diffs)

class NAACAdapter(_HttpAdapter):
    SOURCE = "NAAC"; DOC_TYPES = {"NAAC_CERTIFICATE"}; URL_ENV = "NAAC_URL"; KEY_ENV = "NAAC_KEY"
class NBAAdapter(_HttpAdapter):
    SOURCE = "NBA"; DOC_TYPES = {"NBA_CERTIFICATE"}; URL_ENV = "NBA_URL"; KEY_ENV = "NBA_KEY"
class MCA21Adapter(_HttpAdapter):
    SOURCE = "MCA21"; DOC_TYPES = {"SOCIETY_REGISTRATION"}; URL_ENV = "MCA21_URL"; KEY_ENV = "MCA21_KEY"
class AISHEAdapter(_HttpAdapter):
    SOURCE = "AISHE"; DOC_TYPES = {"STATE_NOC"}; URL_ENV = "AISHE_URL"; KEY_ENV = "AISHE_KEY"

class DigiLockerAdapter(_HttpAdapter):
    """DigiLocker issued-document verification (digitally signed record / QR / URI)."""
    SOURCE = "DIGILOCKER"; DOC_TYPES = {"FIRE_SAFETY_NOC", "LAND_DOCUMENT", "AFFIDAVIT"}
    URL_ENV = "DIGILOCKER_URL"; KEY_ENV = "DIGILOCKER_KEY"

ADAPTERS = {a.SOURCE: a for a in (NAACAdapter(), NBAAdapter(), MCA21Adapter(), AISHEAdapter(), DigiLockerAdapter())}

def adapter_for(doc_type: str):
    for a in ADAPTERS.values():
        if a.can_verify(doc_type):
            return a
    return None

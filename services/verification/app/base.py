from dataclasses import dataclass, field
from enum import Enum
import hashlib, json

class VStatus(str, Enum):
    PENDING = "VERIFICATION_PENDING"
    QUERYING = "QUERYING"
    VERIFIED = "VERIFIED"
    MISMATCH = "MISMATCH_DETECTED"
    EXPIRED = "EXPIRED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    MANUAL_REVIEW = "MANUAL_REVIEW_REQUIRED"

TERMINAL = {VStatus.VERIFIED, VStatus.MISMATCH, VStatus.EXPIRED, VStatus.MANUAL_REVIEW}

class SourceUnavailable(Exception):
    pass

@dataclass
class VerificationResult:
    status: VStatus
    source: str
    query_params: dict = field(default_factory=dict)
    source_response: dict = field(default_factory=dict)
    discrepancies: list = field(default_factory=list)

    @property
    def evidence_hash(self) -> str:
        """SHA-256 of canonical source response: tamper-evident proof of what the source said."""
        return hashlib.sha256(json.dumps(self.source_response, sort_keys=True, default=str).encode()).hexdigest()

class BaseVerificationAdapter:
    """Every external source adapter must implement this."""
    SOURCE = "BASE"
    DOC_TYPES: set = set()

    def can_verify(self, document_type: str) -> bool:
        return document_type in self.DOC_TYPES

    def verify(self, document_data: dict) -> VerificationResult:
        raise NotImplementedError

    def get_source_name(self) -> str:
        return self.SOURCE

def compare(submitted: dict, official: dict, keys):
    """Return list of discrepancies between submitted fields and official source fields."""
    out = []
    for k in keys:
        s, o = submitted.get(k), official.get(k)
        if s is not None and o is not None and str(s).strip().lower() != str(o).strip().lower():
            out.append({"field": k, "submitted": s, "official": o})
    return out

from services.verification.app.adapters import NAACAdapter
from services.verification.app.base import VStatus, SourceUnavailable
import pytest

def d(num, **k): return {"fields": {"certificate_number": num, "institute_id": "1-1", "valid_until": "2099-01-01", **k}}
def test_verified(): assert NAACAdapter().verify(d("N123")).status == VStatus.VERIFIED
def test_mismatch(): assert NAACAdapter().verify(d("N123X")).status == VStatus.MISMATCH
def test_expired(): assert NAACAdapter().verify(d("N123E")).status == VStatus.EXPIRED
def test_outage():
    with pytest.raises(SourceUnavailable): NAACAdapter().verify(d("N123U"))
def test_hash_stable():
    a = NAACAdapter().verify(d("N1")); b = NAACAdapter().verify(d("N1"))
    assert a.evidence_hash == b.evidence_hash

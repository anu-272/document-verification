import sys, types
# anomaly tasks import celery/db; we only test the pure fusion function
from services.anomaly.app.tasks import fuse

def r(t, s): return {"flag_type": t, "score": s}

def test_weighted_fusion():
    res = [r("ELA_EDIT_DETECTED", 1.0), r("METADATA_INCONSISTENT", 0.0), r("FONT_MISMATCH", 0.0),
           r("DUPLICATE_DOCUMENT", 0.0), r("IDENTIFIER_MISMATCH", 0.0)]
    assert fuse(res) == 0.5   # 0.35 raised to 0.5 floor because one very strong signal
def test_clean():
    assert fuse([r("ELA_EDIT_DETECTED", 0.0), r("METADATA_INCONSISTENT", 0.0)]) == 0.0

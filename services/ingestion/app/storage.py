import io
from minio import Minio
from shared.config import *

_c = None
def _client():
    global _c
    if _c is None:
        _c = Minio(MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, secure=False)
        if not _c.bucket_exists(MINIO_BUCKET):
            _c.make_bucket(MINIO_BUCKET)
    return _c

def put(key: str, data: bytes):
    _client().put_object(MINIO_BUCKET, key, io.BytesIO(data), len(data))

def get(key: str) -> bytes:
    r = _client().get_object(MINIO_BUCKET, key)
    try:
        return r.read()
    finally:
        r.close(); r.release_conn()

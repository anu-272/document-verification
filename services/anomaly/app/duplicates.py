"""Duplicate detection: Qdrant vector similarity + SimHash on text for near-duplicates."""
import hashlib
from shared.config import QDRANT_URL

COLLECTION = "documents"
DIM = 256

def _q():
    from qdrant_client import QdrantClient
    return QdrantClient(url=QDRANT_URL, timeout=5)

def _ensure(q):
    from qdrant_client.models import VectorParams, Distance
    names = [c.name for c in q.get_collections().collections]
    if COLLECTION not in names:
        q.create_collection(COLLECTION, vectors_config=VectorParams(size=DIM, distance=Distance.COSINE))

def upsert_vector(doc_id: str, vec: list, payload: dict):
    from qdrant_client.models import PointStruct
    q = _q(); 
    if len(vec) != DIM:  # Gemini embeddings are 768-d; pad/truncate to a fixed collection dim
        vec = (vec + [0.0] * DIM)[:DIM]
    _ensure(q)
    q.upsert(COLLECTION, [PointStruct(id=doc_id, vector=vec, payload=payload)])

def nearest(vec: list, exclude_id: str, limit=3):
    q = _q(); _ensure(q)
    if len(vec) != DIM:
        vec = (vec + [0.0] * DIM)[:DIM]
    hits = q.search(COLLECTION, query_vector=vec, limit=limit + 1)
    return [h for h in hits if str(h.id) != exclude_id][:limit]

def simhash(text: str, bits=64) -> int:
    v = [0] * bits
    toks = text.lower().split()
    for i in range(len(toks) - 2):
        h = int(hashlib.md5(" ".join(toks[i:i + 3]).encode()).hexdigest(), 16)
        for b in range(bits):
            v[b] += 1 if (h >> b) & 1 else -1
    return sum(1 << b for b in range(bits) if v[b] > 0)

def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")

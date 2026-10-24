"""Thin Gemini wrapper with deterministic fallback so the platform works offline."""
import requests
from shared.config import GEMINI_API_KEY, GEMINI_MODEL

def explain(prompt: str, fallback: str) -> str:
    if not GEMINI_API_KEY:
        return fallback
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        r = requests.post(url, params={"key": GEMINI_API_KEY}, timeout=15,
                          json={"contents": [{"parts": [{"text": prompt}]}]})
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return fallback

def embed(text: str) -> list:
    """text-embedding-004; falls back to a hashed bag-of-words vector (dim 256)."""
    if GEMINI_API_KEY:
        try:
            url = "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent"
            r = requests.post(url, params={"key": GEMINI_API_KEY}, timeout=15,
                              json={"content": {"parts": [{"text": text}]}})
            r.raise_for_status()
            return r.json()["embedding"]["values"]
        except Exception:
            pass
    import hashlib
    v = [0.0] * 256
    for tok in text.lower().split():
        v[int(hashlib.md5(tok.encode()).hexdigest(), 16) % 256] += 1.0
    n = sum(x * x for x in v) ** 0.5 or 1.0
    return [x / n for x in v]

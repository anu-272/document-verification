"""Five independent anomaly checks. Each returns
{"score": 0..1, "flag_type": str, "reason": str, "region": dict|None}."""
import io, re
import numpy as np
from datetime import date
from shared.db import conn
from shared.gemini import embed
from shared import config
from services.ingestion.app import storage
from . import duplicates

def _doc(doc_id):
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT * FROM documents WHERE id=%s", (doc_id,))
        return cur.fetchone()

# ---------- 1. ELA (Error Level Analysis) ----------
def ela_analysis(doc_id: str) -> dict:
    import cv2
    from services.ingestion.app.preprocess import load_pages
    d = _doc(doc_id)
    pages = load_pages(storage.get(d["minio_key"]), d["filename"] or "x.pdf")
    best = {"score": 0.0, "region": None}
    for pi, img in enumerate(pages[:5], 1):
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        rec = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        diff = cv2.absdiff(img, rec).astype(np.float32).mean(axis=2)
        diff = cv2.GaussianBlur(diff, (15, 15), 0)
        mu, sd = diff.mean(), diff.std() + 1e-6
        z = (diff - mu) / sd
        mask = (z > 4).astype(np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            continue
        c = max(cnts, key=cv2.contourArea)
        frac = cv2.contourArea(c) / (img.shape[0] * img.shape[1])
        score = float(min(1.0, frac * 60))
        if score > best["score"]:
            x, y, w, h = cv2.boundingRect(c)
            best = {"score": score, "region": {"page": pi, "x1": int(x), "y1": int(y), "x2": int(x + w), "y2": int(y + h)}}
    # Optional learned model
    import os
    if os.getenv("ELA_CNN_WEIGHTS"):
        try:
            from .ela_cnn import predict
            best["score"] = max(best["score"], predict(pages[0]))
        except Exception:
            pass
    return {"score": best["score"], "flag_type": "ELA_EDIT_DETECTED", "region": best["region"],
            "reason": "JPEG re-compression inconsistency suggests a locally edited region" if best["score"] > 0.2 else "No compression anomalies"}

# ---------- 2. Metadata ----------
def metadata_analysis(doc_id: str) -> dict:
    d = _doc(doc_id)
    if not (d["filename"] or "").lower().endswith(".pdf"):
        return {"score": 0.0, "flag_type": "METADATA_INCONSISTENT", "reason": "Not a PDF", "region": None}
    import fitz
    m = fitz.open(stream=storage.get(d["minio_key"]), filetype="pdf").metadata or {}
    score, reasons = 0.0, []
    producer = (m.get("producer") or "") + " " + (m.get("creator") or "")
    if re.search(r"photoshop|gimp|canva|ilovepdf|smallpdf|sejda|foxit phantom|pdfescape|acrobat pro edit", producer, re.I):
        score += 0.5; reasons.append(f"Edited with editing/conversion tool ({producer.strip()})")
    cd, md = m.get("creationDate"), m.get("modDate")
    if cd and md and cd != md:
        score += 0.3; reasons.append("Modification date differs from creation date")
    yr = re.search(r"D:(\d{4})", cd or "")
    if yr and int(yr.group(1)) > date.today().year:
        score += 0.4; reasons.append("Creation date is in the future")
    return {"score": min(score, 1.0), "flag_type": "METADATA_INCONSISTENT",
            "reason": "; ".join(reasons) or "Metadata consistent", "region": None}

# ---------- 3. Font ----------
def font_analysis(doc_id: str) -> dict:
    d = _doc(doc_id)
    if not (d["filename"] or "").lower().endswith(".pdf"):
        return {"score": 0.0, "flag_type": "FONT_MISMATCH", "reason": "Not a PDF", "region": None}
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTChar, LTTextContainer
    fonts = {}
    for pi, page in enumerate(extract_pages(io.BytesIO(storage.get(d["minio_key"]))), 1):
        for el in page:
            if isinstance(el, LTTextContainer):
                for line in el:
                    for ch in line:
                        if isinstance(ch, LTChar):
                            fonts.setdefault(ch.fontname.split("+")[-1], []).append((pi, ch.bbox))
    if not fonts:
        return {"score": 0.0, "flag_type": "FONT_MISMATCH", "reason": "No text layer to analyse", "region": None}
    total = sum(len(v) for v in fonts.values())
    rare = {f: v for f, v in fonts.items() if len(v) / total < 0.02 and len(fonts) > 2}
    if not rare:
        return {"score": 0.0, "flag_type": "FONT_MISMATCH", "reason": "Font usage consistent", "region": None}
    f, v = max(rare.items(), key=lambda kv: len(kv[1]))
    pg, bb = v[0]
    return {"score": min(1.0, 0.4 + 0.1 * len(rare)), "flag_type": "FONT_MISMATCH",
            "reason": f"Isolated font '{f}' appears in a small region ({len(v)} chars) amid a different dominant font",
            "region": {"page": pg, "x1": int(bb[0]), "y1": int(bb[1]), "x2": int(bb[2]), "y2": int(bb[3])}}

# ---------- 4. Duplicate ----------
def duplicate_check(doc_id: str) -> dict:
    d = _doc(doc_id)
    text = (d["extracted_json"] or {}).get("text", "")
    # exact duplicate by hash within other applications
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT id,application_id FROM documents WHERE content_sha256=%s AND id<>%s",
                    (d["content_sha256"], doc_id))
        exact = cur.fetchall()
    if exact:
        other = exact[0]
        same_app = other["application_id"] == d["application_id"]
        return {"score": 0.6 if same_app else 1.0, "flag_type": "DUPLICATE_DOCUMENT", "region": None,
                "reason": f"Byte-identical to document {other['id']} from application {other['application_id']}"}
    best = 0.0; why = "No near-duplicates found"
    try:
        hits = duplicates.nearest(embed(text[:4000]), doc_id)
        sh = duplicates.simhash(text)
        for h in hits:
            if h.payload.get("application_id") == d["application_id"]:
                continue
            with conn() as c:
                cur = c.cursor()
                cur.execute("SELECT extracted_json FROM documents WHERE id=%s", (str(h.id),))
                row = cur.fetchone()
            other_text = ((row or {}).get("extracted_json") or {}).get("text", "")
            ham = duplicates.hamming(sh, duplicates.simhash(other_text)) if other_text else 64
            if h.score > 0.95 and ham < 10:
                s = min(1.0, 0.7 + (10 - ham) * 0.03)
                if s > best:
                    best, why = s, f"Near-duplicate of document {h.id} in application {h.payload.get('application_id')} (cosine={h.score:.3f}, simhash distance={ham})"
    except Exception as e:
        why = f"Duplicate index unavailable ({type(e).__name__}); exact-hash check only"
    return {"score": best, "flag_type": "DUPLICATE_DOCUMENT", "reason": why, "region": None}

# ---------- 5. Identifier ----------
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
def identifier_check(doc_id: str) -> dict:
    d = _doc(doc_id)
    f = (d["extracted_json"] or {}).get("fields", {})
    issues = []
    if f.get("pan") and not PAN_RE.match(f["pan"]):
        issues.append("PAN format invalid")
    iss, val = f.get("issue_date"), f.get("valid_until")
    try:
        if iss and val and date.fromisoformat(val) < date.fromisoformat(iss):
            issues.append("Validity ends before issue date")
        if iss and date.fromisoformat(iss) > date.today():
            issues.append("Issue date is in the future")
    except ValueError:
        issues.append("Irregular date format")
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT institute_id FROM (SELECT extracted_json->'fields'->>'institute_id' AS institute_id "
                    "FROM documents WHERE application_id=%s AND id<>%s) t WHERE institute_id IS NOT NULL",
                    (d["application_id"], doc_id))
        others = {r["institute_id"] for r in cur.fetchall()}
    if f.get("institute_id") and others and f["institute_id"] not in others:
        issues.append("Institute ID differs from other documents in the application")
    return {"score": min(1.0, 0.5 * len(issues)), "flag_type": "IDENTIFIER_MISMATCH",
            "reason": "; ".join(issues) or "Identifiers consistent", "region": None}

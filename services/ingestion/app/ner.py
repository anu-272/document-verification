"""Step 4: structured field extraction (regex + spaCy NER when available)."""
import re
from datetime import datetime

DATE_PATTERNS = [r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", r"\b(\d{4})-(\d{2})-(\d{2})\b"]
FIELD_RE = {
    "certificate_number": r"(?:certificate|ref(?:erence)?|noc|letter)\s*(?:no\.?|number|#)\s*[:\-]?\s*([A-Z0-9/\-]{4,})",
    "valid_until": r"(?:valid\s*(?:up\s*)?(?:to|till|until)|expiry(?: date)?|expires?\s*on)\s*[:\-]?\s*([0-9]{1,4}[/-][0-9]{1,2}[/-][0-9]{1,4})",
    "issue_date": r"(?:date of issue|issued on|dated?)\s*[:\-]?\s*([0-9]{1,4}[/-][0-9]{1,2}[/-][0-9]{1,4})",
    "institute_id": r"(?:institute|institution|aicte)\s*(?:id|code|no\.?)\s*[:\-]?\s*([A-Z0-9\-/]{4,})",
    "pan": r"\b([A-Z]{5}[0-9]{4}[A-Z])\b",
    "amount": r"(?:rs\.?|inr|₹)\s*([0-9,]+(?:\.[0-9]+)?)",
}
_nlp = None

def _norm_date(s: str):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return None

def extract_fields(text: str) -> dict:
    out = {}
    for k, pat in FIELD_RE.items():
        m = re.search(pat, text, re.I if k != "pan" else 0)
        if m:
            v = m.group(1).strip()
            out[k] = _norm_date(v) if k in ("valid_until", "issue_date") else v
            if out[k] is None:
                out[k] = v
    global _nlp
    try:
        if _nlp is None:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        doc = _nlp(text[:20000])
        orgs = [e.text for e in doc.ents if e.label_ == "ORG"]
        if orgs:
            out["institute_name"] = orgs[0]
        out["entities"] = [{"text": e.text, "label": e.label_} for e in doc.ents][:50]
    except Exception:
        pass
    return out

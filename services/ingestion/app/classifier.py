"""Step 3: document classification.
Uses LayoutLMv3 fine-tuned checkpoint if LAYOUTLM_MODEL_DIR is set, otherwise a keyword
scorer so the pipeline runs without GPU/model weights."""
import os, re

KEYWORDS = {
    "FIRE_SAFETY_NOC": ["fire", "safety", "no objection", "fire service"],
    "STATE_NOC": ["no objection certificate", "state government", "essentiality"],
    "NAAC_CERTIFICATE": ["naac", "accreditation", "grade", "cgpa"],
    "NBA_CERTIFICATE": ["national board of accreditation", "nba", "programme accredited"],
    "AFFIDAVIT": ["affidavit", "solemnly affirm", "notary", "deponent"],
    "TER_PAYMENT_RECEIPT": ["transaction", "payment", "receipt", "ter", "fee"],
    "LAND_DOCUMENT": ["sale deed", "lease deed", "khasra", "plot", "land"],
    "BUILDING_PLAN": ["floor plan", "scale", "sq.m", "layout", "sanctioned plan"],
    "SOCIETY_REGISTRATION": ["society", "trust", "registrar", "registration certificate", "memorandum"],
}
_model = None

def _layoutlm(pages, text):
    global _model
    from transformers import pipeline
    if _model is None:
        _model = pipeline("image-classification", model=os.environ["LAYOUTLM_MODEL_DIR"])
    from PIL import Image
    import cv2
    img = Image.fromarray(cv2.cvtColor(pages[0], cv2.COLOR_BGR2RGB))
    top = _model(img)[0]
    return top["label"], float(top["score"])

def classify(pages, text: str):
    if os.getenv("LAYOUTLM_MODEL_DIR"):
        try:
            return _layoutlm(pages, text)
        except Exception:
            pass
    t = text.lower()
    scores = {k: sum(len(re.findall(re.escape(w), t)) for w in v) for k, v in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return "UNKNOWN", 0.0
    return best, round(scores[best] / total, 3)

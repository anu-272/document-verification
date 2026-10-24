"""Step 2: OCR. Azure Document Intelligence primary, Tesseract fallback."""
import io
import cv2
from shared.config import AZURE_DI_ENDPOINT, AZURE_DI_KEY

def _tesseract(pages):
    import pytesseract
    texts, confs = [], []
    for p in pages:
        d = pytesseract.image_to_data(p, output_type=pytesseract.Output.DICT)
        words = [(w, int(c)) for w, c in zip(d["text"], d["conf"]) if w.strip() and int(c) >= 0]
        texts.append(" ".join(w for w, _ in words))
        confs += [c for _, c in words]
    return "\n\f".join(texts), (sum(confs) / len(confs) / 100 if confs else 0.0), "tesseract"

def _azure(raw_pages):
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential
    client = DocumentIntelligenceClient(AZURE_DI_ENDPOINT, AzureKeyCredential(AZURE_DI_KEY))
    texts, confs = [], []
    for p in raw_pages:
        ok, buf = cv2.imencode(".png", p)
        res = client.begin_analyze_document("prebuilt-layout", body=io.BytesIO(buf.tobytes())).result()
        texts.append(res.content)
        for pg in res.pages:
            confs += [w.confidence for w in (pg.words or [])]
    return "\n\f".join(texts), (sum(confs) / len(confs) if confs else 0.0), "azure_di"

def run_ocr(raw_pages, processed_pages):
    if AZURE_DI_ENDPOINT and AZURE_DI_KEY:
        try:
            return _azure(raw_pages)
        except Exception:  # quota exceeded / offline -> fallback
            pass
    return _tesseract(processed_pages)

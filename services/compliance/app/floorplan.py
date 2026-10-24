"""Floor plan processor (OpenCV): scale detection -> room contours -> area -> OCR room labels."""
import re
import cv2, numpy as np

def detect_scale(img, text: str, default_px_per_m=None):
    """Find scale from text like '1 : 100' / 'scale 1cm = 2m' / '10 m' scale-bar label. Returns pixels per metre."""
    m = re.search(r"1\s*cm\s*=\s*(\d+(?:\.\d+)?)\s*m", text, re.I)
    if m:
        return 100.0 / float(m.group(1)) * (img.shape[1] / 2000)  # assumes ~2000px = A3 width at 200dpi, tunable
    m = re.search(r"scale\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(?:px|pixels)\s*=\s*1\s*m", text, re.I)
    if m:
        return float(m.group(1))
    return default_px_per_m

def process(img, px_per_m=None) -> dict:
    import pytesseract
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    full_text = pytesseract.image_to_string(gray)
    scale = detect_scale(img, full_text, px_per_m)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    bw = cv2.dilate(bw, np.ones((3, 3), np.uint8))  # close small wall gaps
    cnts, hier = cv2.findContours(bw, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    H, W = gray.shape; rooms = {}
    for i, c in enumerate(cnts):
        if hier[0][i][3] == -1:  # keep inner contours = enclosed rooms
            continue
        area_px = cv2.contourArea(c)
        if area_px < 0.002 * H * W or area_px > 0.5 * H * W:
            continue
        x, y, w, h = cv2.boundingRect(c)
        roi = gray[y:y + h, x:x + w]
        label = re.sub(r"[^A-Za-z ]", "", pytesseract.image_to_string(roi, config="--psm 6")).strip().lower()
        label = label or f"room_{len(rooms) + 1}"
        area_sqm = area_px / (scale ** 2) if scale else None
        rooms[label] = {"area_sqm": round(area_sqm, 1) if area_sqm else None, "area_px": int(area_px),
                        "bbox": [x, y, x + w, y + h]}
    return {"scale_px_per_m": scale, "scale_detected": scale is not None, "rooms": rooms}

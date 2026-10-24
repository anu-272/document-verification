"""Step 1: image pre-processing (OpenCV): grayscale, denoise, deskew, binarise."""
import cv2, numpy as np

def preprocess(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    coords = np.column_stack(np.where(gray < 200))
    if len(coords) > 50:
        angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        if abs(angle) > 0.3:
            h, w = gray.shape
            M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
            gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_REPLICATE)
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, 31, 15)

def load_pages(data: bytes, filename: str):
    """Return list of BGR numpy page images from a PDF or image."""
    if filename.lower().endswith(".pdf"):
        import fitz
        doc = fitz.open(stream=data, filetype="pdf")
        pages = []
        for p in doc:
            pix = p.get_pixmap(dpi=200)
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
            pages.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR if pix.n == 3 else cv2.COLOR_RGBA2BGR))
        return pages
    arr = np.frombuffer(data, dtype=np.uint8)
    return [cv2.imdecode(arr, cv2.IMREAD_COLOR)]

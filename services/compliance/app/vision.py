"""YOLO object detection over photos / sampled video frames (1 frame / 5 s)."""
import os
import cv2

CLASSES = ["computer_workstation", "lab_bench", "bookshelf", "projector", "smartboard",
           "wheelchair_ramp", "fire_extinguisher", "electrical_panel"]
CONF_MIN = float(os.getenv("VISION_CONF_MIN", "0.6"))
_model = None

def _load():
    global _model
    if _model is None:
        from ultralytics import YOLO
        _model = YOLO(os.getenv("YOLO_WEIGHTS", "yolo11n.pt"))  # replace with fine-tuned AICTE weights
    return _model

def sample_frames(video_path: str, every_s: float = 5.0):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    step = int(fps * every_s); i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if i % step == 0:
            yield frame
        i += 1
    cap.release()

def detect(images) -> dict:
    """Returns {class: {"count": max count in any single frame, "max_conf": float}} for conf >= CONF_MIN.
    Max-per-frame (not sum) avoids double-counting the same objects across frames."""
    model = _load()
    out = {}
    for img in images:
        res = model.predict(img, verbose=False, conf=CONF_MIN)[0]
        per = {}
        for b in res.boxes:
            name = res.names[int(b.cls)]
            per.setdefault(name, []).append(float(b.conf))
        for name, confs in per.items():
            o = out.setdefault(name, {"count": 0, "max_conf": 0.0})
            o["count"] = max(o["count"], len(confs)); o["max_conf"] = max(o["max_conf"], max(confs))
    return out

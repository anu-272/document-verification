"""Small CNN classifier over ELA images (real vs tampered). Train with train_ela.py on a labelled
set; set ELA_CNN_WEIGHTS to the saved .pt path to enable it in the ELA check."""
import os
import cv2, numpy as np, torch, torch.nn as nn

class ELANet(nn.Module):
    def __init__(self):
        super().__init__()
        def blk(i, o): return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(), nn.MaxPool2d(2))
        self.f = nn.Sequential(blk(3, 16), blk(16, 32), blk(32, 64), blk(64, 64))
        self.head = nn.Sequential(nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Linear(64, 1))
    def forward(self, x): return self.head(self.f(x))

def ela_image(img_bgr, quality=90, size=256):
    ok, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    diff = cv2.absdiff(img_bgr, cv2.imdecode(buf, 1))
    diff = cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)
    return cv2.resize(diff, (size, size)).astype(np.float32) / 255.0

_m = None
def predict(img_bgr) -> float:
    global _m
    if _m is None:
        _m = ELANet(); _m.load_state_dict(torch.load(os.environ["ELA_CNN_WEIGHTS"], map_location="cpu")); _m.eval()
    x = torch.from_numpy(ela_image(img_bgr)).permute(2, 0, 1).unsqueeze(0)
    with torch.no_grad():
        return float(torch.sigmoid(_m(x))[0, 0])

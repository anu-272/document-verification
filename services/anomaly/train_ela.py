"""Usage: python train_ela.py data/ (expects data/real/*.jpg|png and data/tampered/*.jpg|png)"""
import sys, glob, torch, torch.nn as nn, cv2, numpy as np
from services.anomaly.app.ela_cnn import ELANet, ela_image

root = sys.argv[1]
X, y = [], []
for label, name in ((0, "real"), (1, "tampered")):
    for p in glob.glob(f"{root}/{name}/*"):
        img = cv2.imread(p)
        if img is not None:
            X.append(ela_image(img)); y.append(label)
X = torch.tensor(np.stack(X)).permute(0, 3, 1, 2); y = torch.tensor(y, dtype=torch.float32).unsqueeze(1)
m = ELANet(); opt = torch.optim.Adam(m.parameters(), 1e-3); loss_fn = nn.BCEWithLogitsLoss()
for epoch in range(20):
    perm = torch.randperm(len(X))
    for i in range(0, len(X), 16):
        idx = perm[i:i + 16]
        opt.zero_grad(); loss = loss_fn(m(X[idx]), y[idx]); loss.backward(); opt.step()
    print(f"epoch {epoch} loss {loss.item():.4f}")
torch.save(m.state_dict(), "ela_cnn.pt")

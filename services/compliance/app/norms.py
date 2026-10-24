"""Configurable norm engine + 4-tier finding classifier."""
import json, os
from pathlib import Path

NORMS_DIR = Path(os.getenv("NORMS_DIR", Path(__file__).resolve().parents[3] / "norms"))
ADVISORY = "Advisory finding only. Physical inspection and final decisions rest with AICTE."

def load_norms(programme_key: str) -> dict:
    return json.loads((NORMS_DIR / f"{programme_key}.json").read_text())

def classify(required, observed, hard_evidence_missing: bool) -> str:
    """ADVISORY_PASS | INSUFFICIENT_EVIDENCE | LIKELY_GAP | RECOMMEND_INSPECT"""
    if observed is None or hard_evidence_missing:
        return "INSUFFICIENT_EVIDENCE"
    ratio = observed / required if required else 1
    if ratio >= 1:
        return "ADVISORY_PASS"
    if ratio >= 0.7:
        return "LIKELY_GAP"
    return "RECOMMEND_INSPECT"

def evaluate(programme_key: str, vision: dict, floorplan: dict, certs: dict) -> list:
    cfg = load_norms(programme_key)
    findings = []
    for key, n in cfg["norms"].items():
        req, observed, ev = n["value"], None, {}
        if n["source"] == "vision":
            v = vision.get(n["class"])
            observed = v["count"] if v else 0 if vision else None
            ev = {"source": "vision", "class": n["class"], "detection": v}
        elif n["source"] == "floorplan":
            for label, r in floorplan.get("rooms", {}).items():
                if n["room_match"] in label and r["area_sqm"]:
                    observed = (observed or 0) + r["area_sqm"]
                    ev = {"source": "floorplan", "room": label, **r}
        elif n["source"] == "certificate":
            raw = certs.get(n["field"])
            try:
                observed = float(raw) if raw is not None else None
            except ValueError:
                observed = None
            ev = {"source": "certificate", "field": n["field"], "value": raw}
        findings.append({"norm_key": key, "required": req, "observed": observed,
                         "finding": classify(req, observed, False), "evidence": ev,
                         "advisory_disclaimer": ADVISORY})
    return findings

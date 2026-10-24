"""Strategy pattern: one evaluator class per rule type; factory selects by rule['type']."""
from datetime import date, timedelta
from abc import ABC, abstractmethod

class Ctx:
    """Evaluation context: documents of one application + institutional record."""
    def __init__(self, docs: list, record: dict):
        self.docs, self.record = docs, record
    def by_type(self, t):
        return [d for d in self.docs if d["doc_type"] == t]

def _res(rule, status, message=None, evidence=None):
    return {"rule_id": rule["rule_id"], "status": status, "severity": rule.get("severity", "MANDATORY"),
            "message": message or (rule.get("message_on_fail") if status == "FAILED" else "OK"),
            "evidence": evidence or {}}

class Evaluator(ABC):
    @abstractmethod
    def evaluate(self, ctx: Ctx, rule: dict) -> dict: ...

class PresenceRule(Evaluator):
    def evaluate(self, ctx, rule):
        docs = ctx.by_type(rule["document_type"])
        if docs:
            return _res(rule, "PASSED", evidence={"doc_id": str(docs[0]["id"])})
        return _res(rule, "FAILED", evidence={"document_type": rule["document_type"]})

class ExpiryRule(Evaluator):
    def evaluate(self, ctx, rule):
        docs = ctx.by_type(rule["document_type"])
        if not docs:
            return _res(rule, "SKIPPED", "Document not submitted (see presence rule)")
        d = docs[0]
        val = (d["extracted_json"] or {}).get("fields", {}).get(rule["field"])
        ev = {"doc_id": str(d["id"]), "field": rule["field"], "value": val}
        if not val:
            return _res(rule, "FAILED", f"Could not read '{rule['field']}' from {rule['document_type']}; manual review needed.", ev)
        try:
            exp = date.fromisoformat(val) + timedelta(days=rule.get("grace_days", 0))
        except ValueError:
            return _res(rule, "FAILED", f"Unparseable date '{val}' in {rule['document_type']}.", ev)
        if exp < date.today():
            return _res(rule, "FAILED", f"{rule['document_type']} expired on {val}", ev)
        return _res(rule, "PASSED", evidence=ev)

class ConsistencyRule(Evaluator):
    def evaluate(self, ctx, rule):
        seen = {}
        for d in ctx.docs:
            if d["doc_type"] in rule["across"]:
                v = (d["extracted_json"] or {}).get("fields", {}).get(rule["field"])
                if v:
                    seen[str(d["id"])] = {"doc_type": d["doc_type"], "value": v}
        values = {x["value"] for x in seen.values()}
        if len(values) > 1:
            return _res(rule, "FAILED", evidence={"field": rule["field"], "values": seen})
        return _res(rule, "PASSED", evidence={"values": seen})

class ThresholdRule(Evaluator):
    def evaluate(self, ctx, rule):
        if "record_field" in rule:
            v = ctx.record.get(rule["record_field"])
            ev = {"source": "AICTE_RECORD", "field": rule["record_field"], "value": v}
        else:
            vals = [d.get("ocr_confidence") for d in ctx.docs if d.get("ocr_confidence") is not None]
            v = min(vals) if vals else None
            ev = {"source": "OCR", "field": rule["doc_field"], "value": v}
        if v is None:
            return _res(rule, "SKIPPED", "No data available", ev)
        return _res(rule, "PASSED" if v >= rule["minimum"] else "FAILED",
                    evidence={**ev, "minimum": rule["minimum"]})

class RecordMatchRule(Evaluator):
    def evaluate(self, ctx, rule):
        docs = ctx.by_type(rule["document_type"])
        if not docs or not ctx.record:
            return _res(rule, "SKIPPED", "No document or institutional record to compare")
        v = (docs[0]["extracted_json"] or {}).get("fields", {}).get(rule["field"])
        rec = ctx.record.get(rule["record_field"])
        ev = {"doc_id": str(docs[0]["id"]), "document_value": v, "record_value": rec}
        if v is None:
            return _res(rule, "FAILED", f"{rule['field']} not found in document.", ev)
        return _res(rule, "PASSED" if str(v) == str(rec) else "FAILED", evidence=ev)

class RuleEvaluatorFactory:
    _reg = {c.__name__: c() for c in (PresenceRule, ExpiryRule, ConsistencyRule, ThresholdRule, RecordMatchRule)}
    @classmethod
    def get(cls, rule_type: str) -> Evaluator:
        if rule_type not in cls._reg:
            raise ValueError(f"Unknown rule type: {rule_type}")
        return cls._reg[rule_type]

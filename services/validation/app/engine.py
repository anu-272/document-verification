import json, os
from pathlib import Path
from .evaluators import Ctx, RuleEvaluatorFactory

RULES_DIR = Path(os.getenv("RULES_DIR", Path(__file__).resolve().parents[3] / "rules"))
CATEGORY_FILES = {"EOA": "eoa_checklist.json", "NEW_PROGRAMME": "new_programme_checklist.json",
                  "INTAKE_INCREASE": "intake_increase_checklist.json"}

def load_checklist(category: str) -> dict:
    """Strategy selection: checklist file determined by application category."""
    fname = CATEGORY_FILES.get(category, CATEGORY_FILES["EOA"])
    cl = json.loads((RULES_DIR / fname).read_text())
    rules = []
    for inc in cl.get("include", []):
        rules += json.loads((RULES_DIR / inc).read_text())["rules"]
    rules += cl["rules"]
    return {"version": cl["version"], "category": cl["application_category"], "rules": rules}

def run_validation(category: str, docs: list, record: dict) -> dict:
    cl = load_checklist(category)
    ctx = Ctx(docs, record)
    results = []
    for rule in cl["rules"]:
        r = RuleEvaluatorFactory.get(rule["type"]).evaluate(ctx, rule)
        r["rule_version"] = cl["version"]
        results.append(r)
    failed = [r for r in results if r["status"] == "FAILED"]
    return {"checklist_version": cl["version"], "category": cl["category"], "results": results,
            "summary": {"total": len(results), "failed": len(failed),
                        "mandatory_failed": sum(1 for r in failed if r["severity"] == "MANDATORY"),
                        "status": "DEFICIENT" if any(r["severity"] == "MANDATORY" for r in failed) else
                                  ("REVIEW" if failed else "COMPLIANT")}}

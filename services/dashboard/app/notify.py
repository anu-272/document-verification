"""Notification engine: configurable alert rules, channels = email (SMTP), SMS (Twilio/MSG91), in-app."""
import json, os, smtplib
from email.message import EmailMessage
from shared import events
from shared.db import conn

DEFAULT_RULES = [
    {"name": "High anomaly score", "event_type": events.ANOMALY_FLAGGED, "condition": {"path": "score", "op": ">", "value": 0.7},
     "channels": ["inapp", "email", "sms"], "notify_role": "OFFICER"},
    {"name": "Mandatory deficiency", "event_type": events.VALIDATION_COMPLETED, "condition": {"path": "mandatory_failed", "op": ">", "value": 0},
     "channels": ["inapp", "email"], "notify_role": "INSTITUTION"},
    {"name": "Verification mismatch/expired", "event_type": events.VERIFICATION_COMPLETED,
     "condition": {"path": "status", "op": "in", "value": ["MISMATCH_DETECTED", "EXPIRED", "MANUAL_REVIEW_REQUIRED"]},
     "channels": ["inapp"], "notify_role": "OFFICER"},
    {"name": "Compliance gap", "event_type": events.COMPLIANCE_COMPLETED, "condition": {"path": "RECOMMEND_INSPECT", "op": ">", "value": 0},
     "channels": ["inapp", "email"], "notify_role": "OFFICER"},
    {"name": "Pipeline failure", "event_type": events.PIPELINE_FAILED, "condition": {"path": "error", "op": "exists"},
     "channels": ["inapp"], "notify_role": "ADMIN"},
]
OPS = {">": lambda a, b: a is not None and a > b, "<": lambda a, b: a is not None and a < b,
       "==": lambda a, b: a == b, "in": lambda a, b: a in b, "exists": lambda a, b: a is not None}

def _match(rule, ev):
    if rule["event_type"] != ev["event_type"]:
        return False
    cond = rule["condition"]
    return OPS[cond["op"]](ev["payload"].get(cond["path"]), cond.get("value"))

def _email(to, subject, body):
    host = os.getenv("SMTP_HOST")
    if not host:
        print(f"[email:dry-run] {to}: {subject}"); return
    m = EmailMessage(); m["From"] = os.getenv("SMTP_FROM", "noreply@aicte-validation.local"); m["To"] = to; m["Subject"] = subject
    m.set_content(body)
    with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", 587))) as s:
        s.starttls(); s.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASS", "")); s.send_message(m)

def _sms(to, body):
    sid, tok = os.getenv("TWILIO_SID"), os.getenv("TWILIO_TOKEN")
    if not sid:
        print(f"[sms:dry-run] {to}: {body}"); return
    import requests
    requests.post(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", auth=(sid, tok), timeout=10,
                  data={"From": os.getenv("TWILIO_FROM"), "To": to, "Body": body})

def evaluate_alerts(ev):
    with conn() as c:
        cur = c.cursor()
        cur.execute("SELECT name,event_type,condition,channels,notify_role FROM alert_rules")
        rules = cur.fetchall() or DEFAULT_RULES
    for rule in rules:
        if not _match(rule, ev):
            continue
        msg = f"[{rule['name']}] application {ev['aggregate_id']}: {ev['event_type']}"
        if "inapp" in rule["channels"]:
            events.client().lpush(f"aicte:inbox:{rule['notify_role']}", json.dumps({"msg": msg, "at": ev["occurred_at"], "event_id": ev["event_id"]}))
            events.client().ltrim(f"aicte:inbox:{rule['notify_role']}", 0, 199)
        to_email = os.getenv(f"ALERT_EMAIL_{rule['notify_role']}")
        if "email" in rule["channels"] and to_email: _email(to_email, msg, msg)
        to_sms = os.getenv(f"ALERT_SMS_{rule['notify_role']}")
        if "sms" in rule["channels"] and to_sms: _sms(to_sms, msg)

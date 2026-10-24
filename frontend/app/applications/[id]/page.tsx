"use client";
import { useEffect, useState } from "react";
import { api } from "../../../lib/api";

export default function Application({ params }: { params: { id: string } }) {
  const [d, setD] = useState<any>(null); const [audit, setAudit] = useState<any[]>([]); const [tab, setTab] = useState("validation");
  useEffect(() => { api(`/api/v1/dashboard/applications/${params.id}`).then(setD); api(`/api/v1/dashboard/applications/${params.id}/audit`).then(setAudit).catch(() => {}); }, []);
  if (!d) return <p>Loading…</p>;
  const badge = (s: string) => <b style={{ color: /FAIL|MISMATCH|EXPIRED|GAP|INSPECT|MANUAL/.test(s) ? "crimson" : /PASS|VERIFIED/.test(s) ? "green" : "#b8860b" }}>{s}</b>;
  return (<div><h2>{params.id}</h2>
    <nav style={{ display: "flex", gap: 12 }}>{["validation", "documents", "verification", "anomalies", "compliance", "audit"].map(t => <a key={t} onClick={() => setTab(t)} style={{ cursor: "pointer", fontWeight: tab === t ? 700 : 400 }}>{t}</a>)}</nav>
    <div style={{ background: "#fff", padding: 16, marginTop: 8 }}>
      {tab === "validation" && d.validation.map((v: any) => <p key={v.rule_id}>{badge(v.status)} {v.rule_id} — {v.plain_message}</p>)}
      {tab === "documents" && d.documents.map((x: any) => <p key={x.id}>{x.filename} · {x.doc_type} · {x.status} · OCR {x.ocr_confidence?.toFixed(2)}</p>)}
      {tab === "verification" && d.verification.map((v: any) => <p key={v.document_id}>{badge(v.status)} {v.source} · {v.checked_at} · <code>{v.evidence_hash?.slice(0, 12)}…</code></p>)}
      {tab === "anomalies" && d.anomalies.map((a: any) => <div key={a.flag_id}><p>{badge(a.flag_type)} score {a.confidence_score?.toFixed(2)} — {a.gemini_explanation || a.reason}</p><small>{a.advisory_disclaimer}</small></div>)}
      {tab === "compliance" && d.compliance.map((c: any) => <p key={c.norm_key}>{badge(c.finding)} {c.norm_key}: required {c.required}, observed {c.observed ?? "n/a"}</p>)}
      {tab === "audit" && audit.map((e: any) => <p key={e.id}><small>{e.occurred_at}</small> {e.event_type} <i>({e.actor})</i></p>)}
    </div></div>);
}

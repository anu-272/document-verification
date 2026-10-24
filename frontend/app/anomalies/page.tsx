"use client";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
export default function Queue() {
  const [q, setQ] = useState<any[]>([]);
  const load = () => api("/api/v1/dashboard/anomaly-queue").then(setQ);
  useEffect(() => { load(); }, []);
  const review = async (id: string, outcome: string) => {
    await fetch(`${process.env.NEXT_PUBLIC_ANOMALY_URL || "http://localhost:8003"}/api/v1/anomalies/${id}/review`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reviewer: "officer", outcome }) });
    setTimeout(load, 1500);
  };
  return (<div><h3>Anomaly review queue</h3><p><small>Preliminary indicators only — human verification required.</small></p>
    {q.map(a => <div key={a.flag_id} style={{ background: "#fff", padding: 12, marginBottom: 8 }}>
      {a.application_id} · {a.flag_type} · {Number(a.confidence_score).toFixed(2)}
      {["CONFIRMED_CONCERN", "FALSE_POSITIVE", "NEEDS_MORE_EVIDENCE"].map(o => <button key={o} style={{ marginLeft: 8 }} onClick={() => review(a.flag_id, o)}>{o}</button>)}</div>)}</div>);
}

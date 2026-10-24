"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, API, token } from "../../lib/api";

export default function Dashboard() {
  const [apps, setApps] = useState<any[]>([]); const [summary, setSummary] = useState<any>(null); const [live, setLive] = useState<string[]>([]);
  const load = () => { api("/api/v1/dashboard/applications").then(setApps); api("/api/v1/dashboard/summary").then(setSummary).catch(() => {}); };
  useEffect(() => {
    load();
    const ws = new WebSocket(`${API.replace("http", "ws")}/ws?token=${token()}`);
    ws.onmessage = m => { const ev = JSON.parse(m.data); setLive(l => [`${ev.event_type} · ${ev.aggregate_id}`, ...l].slice(0, 8)); setTimeout(load, 1000); };
    return () => ws.close();
  }, []);
  return (<div>
    {summary && <div style={{ display: "flex", gap: 16, marginBottom: 16 }}>
      <Card t="Open anomalies" v={summary.open_anomalies} />
      {summary.deficiencies.map((d: any) => <Card key={d.severity} t={`${d.severity} deficiencies`} v={d.n} />)}</div>}
    <h3>Applications</h3>
    <table width="100%" cellPadding={8} style={{ background: "#fff" }}><thead><tr><th>Application</th><th>Docs</th><th>Processed</th><th>Deficiencies</th><th>Open anomalies</th></tr></thead>
      <tbody>{apps.map(a => <tr key={a.application_id}><td><Link href={`/applications/${a.application_id}`}>{a.application_id}</Link></td>
        <td>{a.documents}</td><td>{a.processed}</td><td>{a.deficiencies}</td><td>{a.open_anomalies}</td></tr>)}</tbody></table>
    <h4>Live events</h4><ul>{live.map((l, i) => <li key={i}>{l}</li>)}</ul>
    <p><Link href="/anomalies">Anomaly review queue →</Link></p></div>);
}
const Card = ({ t, v }: any) => <div style={{ background: "#fff", padding: 16, borderRadius: 8, minWidth: 140 }}><div style={{ fontSize: 28 }}>{v}</div><small>{t}</small></div>;

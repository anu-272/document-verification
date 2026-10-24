"use client";
import { useState } from "react";
import { API } from "../../lib/api";
export default function Login() {
  const [u, setU] = useState(""), [p, setP] = useState(""), [err, setErr] = useState("");
  async function submit() {
    const r = await fetch(`${API}/api/v1/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: u, password: p }) });
    if (!r.ok) return setErr("Invalid credentials");
    const d = await r.json(); localStorage.setItem("token", d.token); localStorage.setItem("role", d.role); window.location.href = "/dashboard";
  }
  return (<div style={{ maxWidth: 320, margin: "80px auto", display: "grid", gap: 8 }}><h2>Sign in</h2>
    <input placeholder="Username" value={u} onChange={e => setU(e.target.value)} />
    <input placeholder="Password" type="password" value={p} onChange={e => setP(e.target.value)} />
    <button onClick={submit}>Login</button><span style={{ color: "crimson" }}>{err}</span></div>);
}

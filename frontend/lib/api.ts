export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8006";
export const token = () => (typeof window === "undefined" ? "" : localStorage.getItem("token") || "");
export async function api(path: string, init: RequestInit = {}) {
  const r = await fetch(API + path, { ...init, headers: { "Content-Type": "application/json", Authorization: `Bearer ${token()}`, ...(init.headers || {}) } });
  if (r.status === 401) { if (typeof window !== "undefined") window.location.href = "/login"; throw new Error("unauthorised"); }
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

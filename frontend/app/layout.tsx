export const metadata = { title: "AICTE Validation Platform" };
export default function Root({ children }: { children: React.ReactNode }) {
  return (<html lang="en"><body style={{ fontFamily: "system-ui", margin: 0, background: "#f6f7f9" }}>
    <header style={{ background: "#0b3d91", color: "#fff", padding: "12px 24px" }}>AICTE Approval Validation Platform — <em>decision-support only</em></header>
    <main style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>{children}</main></body></html>);
}

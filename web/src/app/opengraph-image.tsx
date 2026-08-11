import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Salarium 1.0 systematic equity research";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between", background: "#000", color: "#fff", padding: "72px", fontFamily: "Arial, sans-serif", position: "relative" }}>
      <div style={{ position: "absolute", inset: 0, display: "flex", opacity: 0.12, backgroundImage: "linear-gradient(rgba(255,255,255,.18) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.18) 1px, transparent 1px)", backgroundSize: "56px 56px" }} />
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", position: "relative" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "18px" }}>
          <div style={{ width: "44px", height: "44px", border: "1px solid rgba(255,255,255,.25)", display: "flex", alignItems: "center", justifyContent: "center" }}><div style={{ width: "10px", height: "10px", borderRadius: 999, background: "#6ee7b7" }} /></div>
          <div style={{ fontSize: 28, letterSpacing: "8px", fontWeight: 700 }}>SALARIUM</div>
        </div>
        <div style={{ fontSize: 16, letterSpacing: "4px", color: "#6ee7b7" }}>1.0 RELEASE CANDIDATE</div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", position: "relative" }}>
        <div style={{ fontSize: 76, lineHeight: 1.02, fontWeight: 700, maxWidth: 900 }}>Institutional research workflow, built in public.</div>
        <div style={{ marginTop: 28, fontSize: 24, color: "rgba(255,255,255,.5)" }}>Out-of-sample rankings · covariance-aware portfolios · governed risk</div>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", position: "relative", fontSize: 15, letterSpacing: "2px", color: "rgba(255,255,255,.35)" }}><span>OPEN SOURCE QUANTITATIVE EQUITY RESEARCH</span><span>RESEARCH ONLY · NOT INVESTMENT ADVICE</span></div>
    </div>,
    size,
  );
}

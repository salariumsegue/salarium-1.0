import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Salarium — systematic equity research from signal to portfolio";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between", background: "#000", color: "#fff", padding: "72px", fontFamily: "Arial, sans-serif", position: "relative" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", position: "relative" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "18px" }}>
          <svg width="64" height="64" viewBox="0 0 120 120" aria-label="Salarium Imperial Edge Glyph">
            <circle cx="60" cy="60" r="50" fill="none" stroke="#737a76" strokeWidth="6" strokeDasharray="2 5" />
            <path d="M80 35H53c-10.5 0-18 5.8-18 14.2 0 7.1 4.7 11.5 13.7 14l18.7 5.1c3.5 1 5.1 2.3 5.1 4.5 0 3.1-2.8 5.2-7.2 5.2H43l-5 8h28.8C77.5 86 85 80.3 85 71.5c0-7.2-4.6-11.7-13.6-14.2l-18.8-5.2c-3.4-.9-5-2.1-5-4.1 0-2.6 2.6-4.2 6.8-4.2h18.8L80 35Z" fill="#f4f6f4" />
            <path d="M65.2 43.8c.2 3.2-1.2 5.8-4.2 7.8l4.5 1.3 3.6-2.6-1.8-2.2 2.8-1.7-1.5-2.6h-3.4Z" fill="#090b0a" />
            <path d="M18 34l8 4m-10 14 9 1" stroke="#42d98b" strokeWidth="4" />
            <path d="M102 34l-8 4m10 14-9 1" stroke="#e26363" strokeWidth="4" />
          </svg>
          <div style={{ display:"flex", flexDirection:"column" }}><div style={{ fontSize: 28, letterSpacing: "8px", fontWeight: 700 }}>SALARIUM</div><div style={{marginTop:6,fontSize:9,letterSpacing:3,color:"#858b87"}}>AUTONOMOUS INVESTMENT RESEARCH</div></div>
        </div>
        <div style={{ fontSize: 16, letterSpacing: "4px", color: "#6ee7b7" }}>1.0 RELEASE CANDIDATE</div>
      </div>
      <div style={{ display: "flex", flexDirection: "column", position: "relative" }}>
        <div style={{ fontSize: 76, lineHeight: 1.02, fontWeight: 700, maxWidth: 950 }}>Systematic equity research, from signal to portfolio.</div>
        <div style={{ marginTop: 28, fontSize: 24, color: "rgba(255,255,255,.5)" }}>Walk-forward rankings · covariance-aware portfolios · governed risk</div>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", position: "relative", fontSize: 15, letterSpacing: "2px", color: "rgba(255,255,255,.35)" }}><span>OPEN SOURCE QUANTITATIVE EQUITY RESEARCH</span><span>RESEARCH ONLY · NOT INVESTMENT ADVICE</span></div>
    </div>,
    size,
  );
}

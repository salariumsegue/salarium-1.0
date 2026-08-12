import type { SVGProps } from "react";

type GlyphVariant = "color" | "light" | "dark";

const imperialSPath = "M80 35H53c-10.5 0-18 5.8-18 14.2 0 7.1 4.7 11.5 13.7 14l18.7 5.1c3.5 1 5.1 2.3 5.1 4.5 0 3.1-2.8 5.2-7.2 5.2H43l-5 8h28.8C77.5 86 85 80.3 85 71.5c0-7.2-4.6-11.7-13.6-14.2l-18.8-5.2c-3.4-.9-5-2.1-5-4.1 0-2.6 2.6-4.2 6.8-4.2h18.8L80 35Z";
const portraitNotchPath = "M65.2 43.8c.2 3.2-1.2 5.8-4.2 7.8l4.5 1.3 3.6-2.6-1.8-2.2 2.8-1.7-1.5-2.6h-3.4Z";

const marks = Array.from({ length: 24 }, (_, index) => ({
  angle: index * 15,
  side: index >= 14 && index <= 22 ? "positive" : index >= 2 && index <= 10 ? "negative" : "neutral",
  body: index % 3 === 0 ? 8 : index % 3 === 1 ? 6 : 5,
  wick: index % 2 === 0 ? 15 : 13,
}));

export function EdgeGlyph({ className, variant = "color", title = "Salarium Edge Glyph", ...props }: SVGProps<SVGSVGElement> & { variant?: GlyphVariant; title?: string }) {
  const monochrome = variant !== "color";
  const mono = variant === "dark" ? "#090b0a" : "#f4f6f4";
  return (
    <svg viewBox="0 0 120 120" role="img" aria-label={title} className={className} {...props}>
      <title>{title}</title>
      <circle cx="60" cy="60" r="42" fill="none" stroke={monochrome ? mono : "#3b403d"} strokeWidth="1" />
      <g aria-hidden="true">
        {marks.map((mark) => {
          const color = monochrome ? mono : mark.side === "positive" ? "#42d98b" : mark.side === "negative" ? "#e26363" : "#737a76";
          return <g key={mark.angle} transform={`rotate(${mark.angle} 60 60)`}><line x1="60" y1={5 + (15 - mark.wick) / 2} x2="60" y2={5 + (15 + mark.wick) / 2} stroke={color} strokeWidth="1.4" /><rect x="57.7" y={10 - mark.body / 2} width="4.6" height={mark.body} fill={color} /></g>;
        })}
      </g>
      <path d={imperialSPath} fill={monochrome ? mono : "#f4f6f4"} aria-hidden="true" />
      <path d={portraitNotchPath} fill={monochrome ? (variant === "dark" ? "#fff" : "#090b0a") : "#090b0a"} aria-hidden="true" />
      <path d="M44 58.5h29M45 72h27" stroke={monochrome ? (variant === "dark" ? "#fff" : "#090b0a") : "#090b0a"} strokeWidth="1.35" opacity=".48" aria-hidden="true" />
    </svg>
  );
}

export function SalariumLogo({ compact = false, className = "" }: { compact?: boolean; className?: string }) {
  return <span className={`salarium-logo ${className}`}><EdgeGlyph className={compact ? "h-9 w-9" : "h-11 w-11"} />{!compact && <span className="salarium-wordmark"><span>SALARIUM</span><small>AUTONOMOUS INVESTMENT RESEARCH</small></span>}</span>;
}

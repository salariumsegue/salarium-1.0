import type { SVGProps } from "react";

type GlyphVariant = "color" | "light" | "dark";

const classicalProfilePath = "M78 92c-8 3-17 3-23-1-5-3-7-8-5-13l3-7c1-3 0-6-3-8l-4-2c-3-2-3-5-1-8l4-5c-1-3 0-5 3-7 1-12 6-21 15-25 12-5 25 0 29 11 4 10 0 20-5 28-3 5-3 12 0 18l4 8-13 4Z";
const hairPath = "M55 46c1-10 7-17 16-19 10-2 20 2 23 11 2 7 0 14-4 20-3-7-8-10-13-12-7-2-14 0-22 0Z";

const marks = Array.from({ length: 12 }, (_, index) => ({
  angle: index * 30,
  diamond: index % 2 === 1,
  accent: index === 4 || index === 5 || index === 10 || index === 11,
}));

export function EdgeGlyph({ className, variant = "color", title = "Salarium Classical Profile Mark", ...props }: SVGProps<SVGSVGElement> & { variant?: GlyphVariant; title?: string }) {
  const monochrome = variant !== "color";
  const mono = variant === "dark" ? "#090b0a" : "#f4f6f4";
  return (
    <svg viewBox="0 0 120 120" role="img" aria-label={title} className={className} {...props}>
      <title>{title}</title>
      <circle cx="60" cy="60" r="52" fill="none" stroke={monochrome ? mono : "#454c47"} strokeWidth="1.5" />
      <circle cx="60" cy="60" r="47" fill="none" stroke={monochrome ? mono : "#26302a"} strokeWidth="0.75" />
      <g aria-hidden="true">
        {marks.map((mark) => {
          const color = monochrome ? mono : mark.accent ? "#42d98b" : "#848c87";
          return mark.diamond
            ? <rect key={mark.angle} x="57.4" y="11" width="5.2" height="5.2" transform={`rotate(${45 + mark.angle} 60 60)`} fill="none" stroke={color} strokeWidth="1.5" />
            : <path key={mark.angle} d="M56.5 15h7M60 9v12" transform={`rotate(${mark.angle} 60 60)`} fill="none" stroke={color} strokeWidth="1.6" strokeLinecap="square" />;
        })}
      </g>
      <path d={classicalProfilePath} fill={monochrome ? mono : "#f3eddd"} stroke={monochrome ? mono : "#d8d1bf"} strokeWidth="1.25" strokeLinejoin="round" aria-hidden="true" />
      <path d={hairPath} fill={monochrome ? (variant === "dark" ? "#f4f6f4" : "#090b0a") : "#0b3a2a"} aria-hidden="true" />
      <path d="M56 48c6-3 12-2 17 2m-20 5 7 1-5 3m2 7c3 2 6 2 9 0m7-33c6 1 11 5 13 11m-20-9c7-3 14 0 18 5m-21 0c8-3 17 1 21 8" fill="none" stroke={monochrome ? (variant === "dark" ? "#f4f6f4" : "#090b0a") : "#0b3a2a"} strokeWidth="1.8" strokeLinecap="round" aria-hidden="true" />
    </svg>
  );
}

export function SalariumLogo({ compact = false, className = "" }: { compact?: boolean; className?: string }) {
  return <span className={`salarium-logo ${className}`}><EdgeGlyph className={compact ? "h-9 w-9" : "h-11 w-11"} />{!compact && <span className="salarium-wordmark"><span>SALARIUM</span><small>AUTONOMOUS INVESTMENT RESEARCH</small></span>}</span>;
}

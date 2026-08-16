import type { SVGProps } from "react";

type GlyphVariant = "color" | "light" | "dark";

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
      <image href="/salarium-roman-bust.png" x="31" y="24" width="62" height="76" preserveAspectRatio="xMidYMid meet" aria-hidden="true" />
    </svg>
  );
}

export function SalariumLogo({ compact = false, className = "" }: { compact?: boolean; className?: string }) {
  return <span className={`salarium-logo ${className}`}><EdgeGlyph className={compact ? "h-9 w-9" : "h-11 w-11"} />{!compact && <span className="salarium-wordmark"><span>SALARIUM</span><small>AUTONOMOUS INVESTMENT RESEARCH</small></span>}</span>;
}

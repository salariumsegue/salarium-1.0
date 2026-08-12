import Link from "next/link";
import type { ReactNode } from "react";

import { ArrowRightIcon, ArrowUpRightIcon } from "@/components/icons";

export function PageIntro({
  eyebrow,
  title,
  muted,
  description,
  aside,
}: {
  eyebrow: string;
  title: string;
  muted?: string;
  description: string;
  aside?: ReactNode;
}) {
  return (
    <div className="grid gap-8 border-b border-white/10 pb-10 lg:grid-cols-[1fr_auto] lg:items-end">
      <div className="max-w-4xl">
        <p className="eyebrow text-emerald-300">{eyebrow}</p>
        <h1 className="mt-5 text-4xl font-semibold leading-[0.96] tracking-[-0.045em] sm:text-5xl lg:text-7xl">
          {title}{muted && <span className="block text-white/48">{muted}</span>}
        </h1>
        <p className="mt-6 max-w-3xl text-base leading-7 text-white/48 sm:text-lg">{description}</p>
      </div>
      {aside}
    </div>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-7 flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
      <div className="max-w-2xl">
        <p className="eyebrow">{eyebrow}</p>
        <h2 className="mt-3 text-2xl font-semibold tracking-[-0.035em] sm:text-3xl">{title}</h2>
        {description && <p className="mt-3 text-sm leading-6 text-white/42">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function MetricCard({
  label,
  value,
  detail,
  tone = "default",
}: {
  label: string;
  value: string;
  detail: string;
  tone?: "default" | "positive" | "negative";
}) {
  const color = tone === "positive" ? "text-emerald-300" : tone === "negative" ? "text-red-300" : "text-white";
  return (
    <div className="metric-card">
      <p className="text-[9px] font-medium tracking-[0.22em] text-white/30">{label}</p>
      <p className={`mt-5 font-mono text-2xl tracking-[-0.04em] sm:text-3xl ${color}`}>{value}</p>
      <p className="mt-2 text-xs leading-5 text-white/30">{detail}</p>
    </div>
  );
}

export function StatusBadge({ children, tone = "neutral" }: { children: ReactNode; tone?: "positive" | "negative" | "neutral" }) {
  const classes = tone === "positive"
    ? "border-emerald-400/25 bg-emerald-400/[0.06] text-emerald-300"
    : tone === "negative"
      ? "border-red-400/25 bg-red-400/[0.06] text-red-300"
      : "border-white/10 bg-white/[0.025] text-white/45";
  return <span className={`inline-flex items-center border px-2.5 py-1 font-mono text-[9px] tracking-[0.14em] ${classes}`}>{children}</span>;
}

export function InternalCta({ href, children, secondary = false }: { href: string; children: ReactNode; secondary?: boolean }) {
  return (
    <Link href={href} className={secondary ? "button-secondary" : "button-primary"}>
      {children}<ArrowRightIcon className="h-4 w-4" />
    </Link>
  );
}

export function ExternalCta({ href, children, secondary = true }: { href: string; children: ReactNode; secondary?: boolean }) {
  return (
    <a href={href} target="_blank" rel="noreferrer" className={secondary ? "button-secondary" : "button-primary"}>
      {children}<ArrowUpRightIcon className="h-4 w-4" />
    </a>
  );
}

export function PlainEnglish({ children }: { children: ReactNode }) {
  return (
    <div className="border-l-2 border-emerald-400/50 bg-emerald-400/[0.035] px-5 py-4">
      <p className="text-[9px] font-semibold tracking-[0.2em] text-emerald-300">IN PLAIN ENGLISH</p>
      <div className="mt-2 text-sm leading-6 text-white/52">{children}</div>
    </div>
  );
}

export function DisclosurePanel({ items }: { items: string[] }) {
  return (
    <section className="border border-red-400/20 bg-red-400/[0.025] p-6 sm:p-8">
      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <div>
          <p className="eyebrow text-red-300">RESEARCH DISCLOSURE</p>
          <p className="mt-3 text-sm leading-6 text-white/35">What the numbers do—and do not—mean.</p>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {items.map((item) => (
            <div key={item} className="flex gap-3 text-sm leading-6 text-white/45">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-red-300" />
              <span>{item}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

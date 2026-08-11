"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { CloseIcon, GitHubIcon, MenuIcon } from "@/components/icons";
import { GITHUB_URL, NAV_LINKS } from "@/lib/site-config";

export default function SiteHeader({
  version,
  status,
}: {
  version: string;
  status: string;
}) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open]);

  return (
    <header className="site-header">
      <div className="site-container flex h-20 items-center justify-between gap-6">
        <Link href="/" className="group flex items-center gap-3" onClick={() => setOpen(false)}>
          <span className="brand-mark" aria-hidden="true">
            <span className="brand-mark-core" />
          </span>
          <span>
            <span className="block text-[9px] font-medium tracking-[0.34em] text-white/35">AUTONOMOUS EQUITY RESEARCH</span>
            <span className="mt-1 block text-lg font-semibold tracking-[0.22em] text-white transition group-hover:text-emerald-300">SALARIUM</span>
          </span>
        </Link>

        <nav className="hidden items-center gap-1 lg:flex" aria-label="Primary navigation">
          {NAV_LINKS.map((link) => {
            const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
            return (
              <Link key={link.href} href={link.href} className={`nav-link ${active ? "nav-link-active" : ""}`} aria-current={active ? "page" : undefined}>
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-3">
          <div className="hidden items-center gap-2 border border-white/10 bg-black/50 px-3 py-2 text-[9px] tracking-[0.18em] text-white/40 sm:flex">
            <span className="status-dot" />
            <span>{version.toUpperCase()}</span>
            <span className="text-white/15">/</span>
            <span>{status.replaceAll("_", " ").toUpperCase()}</span>
          </div>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
            className="icon-button hidden sm:inline-flex"
            aria-label="Open Salarium on GitHub"
          >
            <GitHubIcon className="h-4 w-4" />
          </a>
          <button
            type="button"
            className="icon-button lg:hidden"
            aria-label={open ? "Close navigation" : "Open navigation"}
            aria-expanded={open}
            aria-controls="mobile-navigation"
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <CloseIcon className="h-5 w-5" /> : <MenuIcon className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {open && (
        <div id="mobile-navigation" className="border-t border-white/10 bg-black/95 lg:hidden">
          <nav className="site-container grid gap-1 py-4" aria-label="Mobile navigation">
            {NAV_LINKS.map((link) => {
              const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center justify-between border px-4 py-4 text-sm tracking-[0.12em] transition ${
                    active
                      ? "border-emerald-400/30 bg-emerald-400/[0.06] text-emerald-300"
                      : "border-white/8 text-white/55 hover:border-white/20 hover:text-white"
                  }`}
                  onClick={() => setOpen(false)}
                  aria-current={active ? "page" : undefined}
                >
                  {link.label.toUpperCase()}
                  <span aria-hidden="true">→</span>
                </Link>
              );
            })}
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer"
              className="mt-2 flex items-center gap-3 border border-white/10 px-4 py-4 text-sm text-white/55"
            >
              <GitHubIcon className="h-4 w-4" />
              VIEW SOURCE ON GITHUB
            </a>
          </nav>
        </div>
      )}
    </header>
  );
}

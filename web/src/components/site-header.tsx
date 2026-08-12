"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { SalariumLogo } from "@/components/edge-glyph";
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
  const toggleRef = useRef<HTMLButtonElement>(null);
  const firstLinkRef = useRef<HTMLAnchorElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        toggleRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";
    firstLinkRef.current?.focus();
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <header className="site-header">
      <div className="site-container flex h-20 items-center justify-between gap-6">
        <Link href="/" className="group" onClick={() => setOpen(false)} aria-label="Salarium home">
          <SalariumLogo />
        </Link>

        <nav className="hidden items-center gap-1 lg:flex" aria-label="Primary navigation">
          {NAV_LINKS.map((link) => {
            const active = pathname.startsWith(link.href);
            return (
              <Link key={link.href} href={link.href} className={`nav-link ${active ? "nav-link-active" : ""}`} aria-current={active ? "page" : undefined}>
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-3">
          <div className="release-status hidden sm:flex" aria-label={`Release ${version}, ${status.replaceAll("_", " ")}`}>
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
            ref={toggleRef}
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
              const active = pathname.startsWith(link.href);
              return (
                <Link
                  ref={link === NAV_LINKS[0] ? firstLinkRef : undefined}
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

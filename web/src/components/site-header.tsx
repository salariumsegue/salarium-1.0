"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { SalariumLogo } from "@/components/edge-glyph";
import { CloseIcon, GitHubIcon, MenuIcon } from "@/components/icons";
import { GITHUB_URL, NAV_GROUPS } from "@/lib/site-config";

export default function SiteHeader({
  version,
  status,
}: {
  version: string;
  status: string;
}) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [activeGroup, setActiveGroup] = useState<string | null>(null);
  const [mobileGroup, setMobileGroup] = useState<string | null>(null);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const firstLinkRef = useRef<HTMLAnchorElement>(null);
  const desktopNavRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const dismiss = (event: PointerEvent) => {
      if (!desktopNavRef.current?.contains(event.target as Node)) setActiveGroup(null);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || !activeGroup) return;
      const group = activeGroup;
      setActiveGroup(null);
      desktopNavRef.current?.querySelector<HTMLButtonElement>(`[data-nav-group="${group}"]`)?.focus();
    };
    document.addEventListener("pointerdown", dismiss);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", dismiss);
      document.removeEventListener("keydown", escape);
    };
  }, [activeGroup]);

  const closeNavigation = () => {
    setOpen(false);
    setActiveGroup(null);
    setMobileGroup(null);
  };

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
        <Link href="/" className="group" onClick={closeNavigation} aria-label="Salarium home">
          <SalariumLogo />
        </Link>

        <nav ref={desktopNavRef} className="hidden items-center gap-1 xl:flex" aria-label="Primary navigation">
          {NAV_GROUPS.map((group) => {
            const active = pathname === group.href || ("items" in group && group.items.some((item) => pathname === item.href && item.href !== "/dashboard"));
            if (!("items" in group)) return (
              <Link key={group.href} href={group.href} className={`nav-link ${active ? "nav-link-active" : ""}`} aria-current={pathname === group.href ? "page" : undefined} onClick={() => setActiveGroup(null)}>
                {group.label}
              </Link>
            );
            return (
              <div key={group.label} className="nav-group" onMouseEnter={() => setActiveGroup(group.label)} onMouseLeave={() => setActiveGroup(null)} onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setActiveGroup(null); }}>
                <button type="button" className={`nav-link nav-group-toggle ${active ? "nav-link-active" : ""}`} data-nav-group={group.label} aria-expanded={activeGroup === group.label} aria-controls={`nav-menu-${group.label.toLowerCase()}`} onClick={() => setActiveGroup(group.label)}>
                  {group.label}<span className="nav-chevron" aria-hidden="true">⌄</span>
                </button>
                {activeGroup === group.label && (
                  <div id={`nav-menu-${group.label.toLowerCase()}`} className="nav-dropdown">
                    {group.items.map((item) => <Link key={item.href} href={item.href} className="nav-dropdown-link" aria-current={pathname === item.href ? "page" : undefined} onClick={closeNavigation}>{item.label}<span aria-hidden="true">↗</span></Link>)}
                  </div>
                )}
              </div>
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
            className="icon-button xl:hidden"
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
        <div id="mobile-navigation" className="border-t border-white/10 bg-black/95 xl:hidden">
          <nav className="site-container mobile-nav" aria-label="Mobile navigation">
            {NAV_GROUPS.map((group, index) => {
              const active = pathname === group.href || ("items" in group && group.items.some((item) => pathname === item.href && item.href !== "/dashboard"));
              if (!("items" in group)) return <Link ref={index === 0 ? firstLinkRef : undefined} key={group.label} href={group.href} className={`mobile-nav-row ${active ? "mobile-nav-active" : ""}`} aria-current={active ? "page" : undefined} onClick={closeNavigation}>{group.label}<span aria-hidden="true">→</span></Link>;
              return <div key={group.label} className="mobile-nav-group">
                <button type="button" className={`mobile-nav-row ${active ? "mobile-nav-active" : ""}`} aria-expanded={mobileGroup === group.label} aria-controls={`mobile-menu-${group.label.toLowerCase()}`} onClick={() => setMobileGroup(mobileGroup === group.label ? null : group.label)}>{group.label}<span aria-hidden="true">{mobileGroup === group.label ? "−" : "+"}</span></button>
                {mobileGroup === group.label && <div id={`mobile-menu-${group.label.toLowerCase()}`} className="mobile-nav-submenu">{group.items.map((item) => <Link key={item.href} href={item.href} aria-current={pathname === item.href ? "page" : undefined} onClick={closeNavigation}>{item.label}<span aria-hidden="true">↗</span></Link>)}</div>}
              </div>;
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

import Link from "next/link";

type NavigationKey =
  | "overview"
  | "rankings"
  | "candidates"
  | "architecture"
  | "research";

const links: Array<{
  key: NavigationKey;
  href: string;
  label: string;
}> = [
  {
    key: "overview",
    href: "/",
    label: "OVERVIEW",
  },
  {
    key: "rankings",
    href: "/rankings",
    label: "RANKINGS",
  },
  {
    key: "candidates",
    href: "/candidates",
    label: "CANDIDATES",
  },
  {
    key: "architecture",
    href: "/architecture",
    label: "ARCHITECTURE",
  },
  {
    key: "research",
    href: "/research",
    label: "RESEARCH",
  },
];

export default function SiteNav({
  active,
}: {
  active: NavigationKey;
}) {
  return (
    <nav className="hidden items-center gap-5 text-[10px] tracking-[0.16em] text-white/45 md:flex lg:text-xs">
      {links.map((link) => (
        <Link
          key={link.key}
          href={link.href}
          className={
            active === link.key
              ? "text-emerald-400"
              : "transition hover:text-white"
          }
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}

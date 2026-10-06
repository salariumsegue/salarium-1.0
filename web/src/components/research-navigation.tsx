"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
const links = [
  ["/dashboard", "Four portfolios"],
  ["/research", "Research overview"],
  ["/research/courtroom", "Oil sleeve case"],
  ["/research/experiments", "Experiments"],
  ["/research/performance", "Historical results"],
  ["/replay", "Earlier decision archive"],
  ["/dependencies", "Business dependencies"],
];
export default function ResearchNavigation() {
  const pathname = usePathname();
  return (
    <nav
      className="research-navigation site-container"
      aria-label="Research sections"
    >
      {links.map(([href, label]) => (
        <Link
          href={href}
          key={href}
          aria-current={pathname === href ? "page" : undefined}
        >
          {label}
        </Link>
      ))}
    </nav>
  );
}

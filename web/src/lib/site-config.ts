function normalizeSiteUrl(value: string): string {
  const trimmed = value.trim().replace(/\/$/, "");
  return /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
}

const configuredSiteUrl =
  process.env.NEXT_PUBLIC_SITE_URL ??
  process.env.VERCEL_PROJECT_PRODUCTION_URL ??
  process.env.VERCEL_URL;

export const SITE_URL = configuredSiteUrl
  ? normalizeSiteUrl(configuredSiteUrl)
  : "http://localhost:3000";

export const GITHUB_URL =
  "https://github.com/salariumsegue/salarium-1.0";

export const RELEASE_BRANCH_URL =
  GITHUB_URL;

export const MODEL_CARD_URL =
  `${GITHUB_URL}/blob/main/docs/SALARIUM_1_0_MODEL_CARD.md`;

export const RELEASE_NOTES_URL =
  `${GITHUB_URL}/blob/main/docs/RELEASE_NOTES_1_0.md`;

export const NAV_LINKS = [
  { href: "/rankings", label: "Rankings" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/research", label: "Research" },
  { href: "/methodology", label: "Methodology" },
  { href: "/architecture", label: "Architecture" },
  { href: "/about", label: "About" },
] as const;

export const RESEARCH_LINKS = [
  { href: "/research/performance", label: "Performance" },
  { href: "/research/experiments", label: "Experiments" },
] as const;

export const SECONDARY_LINKS = [
  { href: "/", label: "Overview" },
  { href: "/candidates", label: "Candidates" },
  { href: "/disclosures", label: "Disclosures" },
] as const;

export const DATA_LINKS = [
  { href: "/data/release_snapshot.json", label: "Release snapshot" },
  { href: "/data/release_rankings_snapshot.json", label: "20D release rankings" },
  { href: "/data/candidate_funnel_snapshot.json", label: "Candidate snapshot" },
] as const;

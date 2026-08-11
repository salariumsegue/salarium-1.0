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
  "https://github.com/salariumsegue/salarium-1.0/tree/release/salarium-1.0-web-production";

export const MODEL_CARD_URL =
  "https://github.com/salariumsegue/salarium-1.0/blob/release/salarium-1.0-web-production/docs/SALARIUM_1_0_MODEL_CARD.md";

export const RELEASE_NOTES_URL =
  "https://github.com/salariumsegue/salarium-1.0/blob/release/salarium-1.0-web-production/docs/RELEASE_NOTES_1_0.md";

export const NAV_LINKS = [
  { href: "/", label: "Overview" },
  { href: "/rankings", label: "Rankings" },
  { href: "/candidates", label: "Candidates" },
  { href: "/architecture", label: "Architecture" },
  { href: "/research", label: "Research" },
  { href: "/about", label: "About" },
] as const;

export const DATA_LINKS = [
  { href: "/data/release_snapshot.json", label: "Release snapshot" },
  { href: "/data/release_rankings_snapshot.json", label: "20D release rankings" },
  { href: "/data/candidate_funnel_snapshot.json", label: "Candidate snapshot" },
] as const;

import process from "node:process";

const RAW_URL = process.argv[2] || process.env.SALARIUM_PRODUCTION_URL;
if (!RAW_URL) {
  console.error("Usage: npm run check:deployment -- https://your-salarium-domain.example");
  console.error("Or set SALARIUM_PRODUCTION_URL.");
  process.exit(2);
}

const BASE_URL = /^https?:\/\//i.test(RAW_URL) ? RAW_URL.replace(/\/$/, "") : `https://${RAW_URL.replace(/\/$/, "")}`;
const HTML_ROUTES = ["/", "/rankings", "/candidates", "/architecture", "/research", "/about", "/disclosures"];
const DATA_ROUTES = ["/data/release_snapshot.json", "/data/release_rankings_snapshot.json", "/data/candidate_funnel_snapshot.json"];
const DISCOVERY_ROUTES = ["/manifest.webmanifest", "/robots.txt", "/sitemap.xml", "/opengraph-image", "/salarium-mark.svg"];

function internalLinks(html) {
  const links = new Set();
  for (const match of html.matchAll(/<a\b[^>]*\bhref=["']([^"']+)["']/gi)) {
    if (match[1].startsWith("/") && !match[1].startsWith("//")) links.add(match[1]);
  }
  return links;
}

function pathOnly(raw) {
  const parsed = new URL(raw, BASE_URL);
  return `${parsed.pathname}${parsed.search}`;
}

function assertHeaders(route, response) {
  const expected = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
  };
  for (const [header, value] of Object.entries(expected)) {
    if (response.headers.get(header) !== value) {
      throw new Error(`${route} missing ${header}=${value}`);
    }
  }
}

const discovered = new Set();

try {
  for (const route of HTML_ROUTES) {
    const response = await fetch(`${BASE_URL}${route}`, { redirect: "follow" });
    if (response.status !== 200) throw new Error(`${route} returned ${response.status}`);
    assertHeaders(route, response);
    const html = await response.text();
    if (!html.toUpperCase().includes("SALARIUM")) throw new Error(`${route} rendered without the Salarium shell`);
    if (!html.includes('id="main-content"')) throw new Error(`${route} rendered without main-content`);
    for (const link of internalLinks(html)) discovered.add(link);
  }

  for (const route of DATA_ROUTES) {
    const response = await fetch(`${BASE_URL}${route}`, { redirect: "follow" });
    if (response.status !== 200) throw new Error(`${route} returned ${response.status}`);
    assertHeaders(route, response);
    await response.json();
  }

  for (const route of DISCOVERY_ROUTES) {
    const response = await fetch(`${BASE_URL}${route}`, { redirect: "follow" });
    if (response.status !== 200) throw new Error(`${route} returned ${response.status}`);
    assertHeaders(route, response);
  }

  for (const raw of discovered) {
    if (raw.startsWith("/#") || raw === "#main-content") continue;
    const response = await fetch(`${BASE_URL}${pathOnly(raw)}`, { redirect: "follow" });
    if (response.status !== 200) throw new Error(`Rendered internal link ${raw} returned ${response.status}`);
  }

  const missing = await fetch(`${BASE_URL}/definitely-not-a-salarium-route`, { redirect: "manual" });
  if (missing.status !== 404) throw new Error(`Unknown route returned ${missing.status}; expected 404`);

  console.log("SALARIUM_DEPLOYMENT_CHECK=PASS");
  console.log(`Origin: ${BASE_URL}`);
  console.log(`HTML routes: ${HTML_ROUTES.length}`);
  console.log(`Data routes: ${DATA_ROUTES.length}`);
  console.log(`Rendered internal destinations: ${discovered.size}`);
} catch (error) {
  console.error("SALARIUM_DEPLOYMENT_CHECK=FAIL");
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
}

import net from "node:net";
import process from "node:process";
import { spawn } from "node:child_process";

const HTML_ROUTES = [
  "/",
  "/rankings",
  "/portfolio",
  "/simulation",
  "/methodology",
  "/candidates",
  "/architecture",
  "/research",
  "/research/performance",
  "/research/experiments",
  "/about",
  "/disclosures",
];
const DATA_ROUTES = [
  "/api/simulation/quotes",
  "/data/release_snapshot.json",
  "/data/release_rankings_snapshot.json",
  "/data/candidate_funnel_snapshot.json",
  "/data/hypothetical_account_snapshot.json",
  "/data/crisis_diversifier_research.json",
  "/data/drawdown_budget_research.json",
];
const DISCOVERY_ROUTES = [
  "/manifest.webmanifest",
  "/robots.txt",
  "/sitemap.xml",
  "/opengraph-image",
  "/salarium-mark.svg",
  "/salarium-edge-glyph.svg",
  "/salarium-logo.svg",
  "/salarium-roman-bust.png",
];

function availablePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (!address || typeof address === "string") {
        server.close(() => reject(new Error("Unable to allocate a smoke-test port")));
        return;
      }
      server.close(() => resolve(address.port));
    });
  });
}

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function waitForServer(baseUrl, child, logs) {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(`Next.js exited before becoming ready (code ${child.exitCode}).\n${logs.join("")}`);
    }
    try {
      const response = await fetch(baseUrl, { redirect: "manual" });
      if (response.ok) return;
    } catch {
      // The server is still starting.
    }
    await sleep(350);
  }
  throw new Error(`Timed out waiting for ${baseUrl}.\n${logs.join("")}`);
}

function stop(child) {
  if (child.exitCode !== null) return;
  try {
    if (process.platform !== "win32") process.kill(-child.pid, "SIGTERM");
    else child.kill("SIGTERM");
  } catch {
    child.kill("SIGTERM");
  }
}

function internalLinks(html) {
  const links = new Set();
  for (const match of html.matchAll(/<a\b[^>]*\bhref=["']([^"']+)["']/gi)) {
    const raw = match[1];
    if (!raw.startsWith("/") || raw.startsWith("//")) continue;
    links.add(raw);
  }
  return links;
}

function pathOnly(raw) {
  const parsed = new URL(raw, "http://salarium.local");
  return `${parsed.pathname}${parsed.search}`;
}

function assertSecurityHeaders(route, response) {
  const required = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
  };
  for (const [header, expected] of Object.entries(required)) {
    if (response.headers.get(header) !== expected) {
      throw new Error(`${route} missing security header ${header}: ${response.headers.get(header)}`);
    }
  }
}

const port = Number(process.env.SALARIUM_SMOKE_PORT || (await availablePort()));
const baseUrl = `http://127.0.0.1:${port}`;
const npm = process.platform === "win32" ? "npm.cmd" : "npm";
const child = spawn(npm, ["run", "start", "--", "-H", "127.0.0.1", "-p", String(port)], {
  cwd: process.cwd(),
  detached: process.platform !== "win32",
  env: { ...process.env, NODE_ENV: "production", NEXT_TELEMETRY_DISABLED: "1" },
  stdio: ["ignore", "pipe", "pipe"],
});
const logs = [];
child.stdout.on("data", (chunk) => logs.push(chunk.toString()));
child.stderr.on("data", (chunk) => logs.push(chunk.toString()));

try {
  await waitForServer(baseUrl, child, logs);

  const discovered = new Set();
  for (const route of HTML_ROUTES) {
    const response = await fetch(`${baseUrl}${route}`, { redirect: "manual" });
    if (response.status !== 200) throw new Error(`${route} returned ${response.status}; expected 200`);
    assertSecurityHeaders(route, response);
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("text/html")) throw new Error(`${route} did not return HTML (${contentType})`);
    const body = await response.text();
    if (!body.toUpperCase().includes("SALARIUM")) throw new Error(`${route} rendered without the Salarium product shell`);
    if (!body.includes('id="main-content"')) throw new Error(`${route} rendered without the main-content landmark`);
    for (const link of internalLinks(body)) discovered.add(link);
  }

  for (const route of DATA_ROUTES) {
    const response = await fetch(`${baseUrl}${route}`, { redirect: "manual" });
    if (response.status !== 200) throw new Error(`${route} returned ${response.status}; expected 200`);
    assertSecurityHeaders(route, response);
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) throw new Error(`${route} did not return JSON (${contentType})`);
    await response.json();
  }

  for (const route of DISCOVERY_ROUTES) {
    const response = await fetch(`${baseUrl}${route}`, { redirect: "manual" });
    if (response.status !== 200) throw new Error(`${route} returned ${response.status}; expected 200`);
    assertSecurityHeaders(route, response);
  }

  for (const raw of discovered) {
    if (raw.startsWith("/#") || raw === "#main-content") continue;
    const route = pathOnly(raw);
    const response = await fetch(`${baseUrl}${route}`, { redirect: "manual" });
    if (response.status !== 200) {
      throw new Error(`Rendered internal link ${raw} returned ${response.status}`);
    }
  }

  const missing = await fetch(`${baseUrl}/definitely-not-a-salarium-route`, { redirect: "manual" });
  if (missing.status !== 404) throw new Error(`Unknown route returned ${missing.status}; expected 404`);

  console.log("SALARIUM_SITE_SMOKE=PASS");
  console.log(`HTML routes served: ${HTML_ROUTES.length}`);
  console.log(`Data artifacts served: ${DATA_ROUTES.length}`);
  console.log(`Rendered internal destinations checked: ${discovered.size}`);
  console.log("Security headers: PASS");
  console.log("404 behavior: PASS");
} catch (error) {
  console.error("SALARIUM_SITE_SMOKE=FAIL");
  console.error(error instanceof Error ? error.message : error);
  if (logs.length) console.error(logs.join(""));
  process.exitCode = 1;
} finally {
  stop(child);
  await sleep(400);
}

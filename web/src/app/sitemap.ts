import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site-config";

const routes = ["/dashboard", "/replay", "/dependencies", "/research/courtroom", "", "/rankings", "/portfolio", "/simulation", "/methodology", "/candidates", "/architecture", "/research", "/research/performance", "/research/experiments", "/about", "/disclosures"];

export default function sitemap(): MetadataRoute.Sitemap {
  return routes.map((route) => ({
    url: `${SITE_URL}${route}`,
    changeFrequency: route === "" ? "weekly" : "monthly",
    priority: route === "" ? 1 : 0.75,
  }));
}

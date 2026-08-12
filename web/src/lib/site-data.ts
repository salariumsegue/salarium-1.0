import fs from "node:fs";
import path from "node:path";

import type {
  CandidateSnapshot,
  DataState,
  PortfolioSnapshot,
  RankingSnapshot,
  ReleaseSnapshot,
} from "@/lib/site-types";

function loadJson<T>(filename: string): T {
  const filePath = path.join(process.cwd(), "public", "data", filename);
  return JSON.parse(fs.readFileSync(filePath, "utf8")) as T;
}

function safeLoadJson<T>(filename: string, validate: (value: unknown) => value is T): DataState<T> {
  const filePath = path.join(process.cwd(), "public", "data", filename);
  if (!fs.existsSync(filePath)) {
    return { status: "unavailable", artifact: `public/data/${filename}`, reason: "The governed public artifact has not been exported." };
  }
  try {
    const value: unknown = JSON.parse(fs.readFileSync(filePath, "utf8"));
    return validate(value)
      ? { status: "available", data: value }
      : { status: "error", artifact: `public/data/${filename}`, reason: "The artifact does not satisfy the website data contract." };
  } catch {
    return { status: "error", artifact: `public/data/${filename}`, reason: "The artifact could not be parsed as JSON." };
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isPortfolioSnapshot(value: unknown): value is PortfolioSnapshot {
  return isRecord(value) && typeof value.schema_version === "string" && typeof value.snapshot_date === "string" && Array.isArray(value.holdings);
}

export function loadReleaseSnapshot(): ReleaseSnapshot {
  return loadJson<ReleaseSnapshot>("release_snapshot.json");
}

export function loadRankingSnapshot(): RankingSnapshot {
  return loadJson<RankingSnapshot>("release_rankings_snapshot.json");
}

export function loadCandidateSnapshot(): CandidateSnapshot {
  return loadJson<CandidateSnapshot>("candidate_funnel_snapshot.json");
}

export function loadPortfolioSnapshot(): DataState<PortfolioSnapshot> {
  return safeLoadJson("portfolio_snapshot.json", isPortfolioSnapshot);
}

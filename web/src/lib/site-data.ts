import fs from "node:fs";
import path from "node:path";

import type {
  CandidateSnapshot,
  RankingSnapshot,
  ReleaseSnapshot,
} from "@/lib/site-types";

function loadJson<T>(filename: string): T {
  const filePath = path.join(process.cwd(), "public", "data", filename);
  return JSON.parse(fs.readFileSync(filePath, "utf8")) as T;
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

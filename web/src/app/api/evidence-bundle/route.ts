import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
export const dynamic = "force-static";
export function GET() {
  const filenames = [
    "forward_paper_snapshot.json",
    "release_snapshot.json",
    "hypothetical_account_snapshot.json",
    "crisis_diversifier_research.json",
    "decision_archive.json",
    "research_return_stream.json",
  ];
  const artifacts = filenames.map((name) => {
    const bytes = fs.readFileSync(
      path.join(process.cwd(), "public/data", name),
    );
    return {
      name,
      sha256: createHash("sha256").update(bytes).digest("hex"),
      raw_utf8: bytes.toString("utf8"),
      data: JSON.parse(bytes.toString("utf8")),
    };
  });
  const bundle = {
    schema_version: "1.0",
    purpose:
      "Reproduce published metric calculations and inspect original recorded decisions. Not a complete model-training or market-input dataset.",
    verification:
      "SHA-256 is calculated over the exact UTF-8 bytes preserved in raw_utf8. Re-serializing data changes the hash.",
    calculations: {
      drawdown: "indicative_nav / high_water_mark - 1",
      nav: "Published indicative_nav; full mark reconstruction requires the archived positions, cash accounting and market inputs, which are not all bundled.",
      annualized_return:
        "product(1 + net_return) ** ((252 / rebalance_every_days) / observation_count) - 1; full-precision observations are included in research_return_stream.json.",
    },
    exclusions: [
      "Taxes",
      "Additional market impact",
      "Capacity limits",
      "Live execution",
      "Full historical raw prices and feature matrix",
    ],
    artifacts,
  };
  return Response.json(bundle, {
    headers: {
      "Content-Disposition":
        'attachment; filename="salarium-research-bundle.json"',
    },
  });
}

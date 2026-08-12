# Salarium public website redesign implementation

## Detected frontend architecture

- Public website root: `web/`.
- Framework: Next.js 16.3 App Router with React 19.2 and strict TypeScript.
- Styling: Tailwind CSS 4 plus the repository-owned token and component layer in `web/src/app/globals.css`.
- Package manager: npm, locked by `web/package-lock.json`.
- Rendering: server components by default; client components only for navigation, ranking exploration, dialogs, and other genuine interaction.
- Internal research UI: Streamlit at `app/streamlit_app.py` and `app/dashboard.py`. It is not part of this redesign.
- Existing public routes before this work: `/`, `/rankings`, `/candidates`, `/architecture`, `/research`, `/about`, and `/disclosures`.
- Existing validation: `npm run lint`, `npm run validate:site`, `npm run build`, `npm run smoke`, and the aggregate `npm run check`. Python research validation is `./venv/bin/python -m pytest -q`; Python lint is available through Ruff.

## Source-of-truth data locations

- `web/public/data/release_snapshot.json`: locked release architecture, overall and yearly walk-forward results, six governed decisions, limitations, and release provenance.
- `web/public/data/release_rankings_snapshot.json`: committed 20-day model, 500-security cross-section dated 2026-06-10, with the top 25 ranks, scores, score percentiles, 20-day volatility, risk state, model configuration, and provenance.
- `web/public/data/candidate_funnel_snapshot.json`: separate broad-universe discovery evidence. It is retained at `/candidates` but is not represented as the release portfolio.
- `reports/experiments/` and `results/`: experiment evidence used by the release exporters. Public components consume the governed JSON boundary rather than parsing arbitrary CSVs at request time.
- `docs/SALARIUM_1_0_MODEL_CARD.md`, `docs/DISCLAIMER.md`, and experiment methodology documents: explanatory and limitation evidence.
- Repository remote: `https://github.com/salariumsegue/salarium-1.0`.
- Current working commit at implementation start: `24a1eb3eb93d56a9c85db7d7ef7d62efa617167c`.

## Verified public evidence

The governed public artifacts verify Liquid-500, a 20-trading-day forward target, 10-trading-day rebalance cadence, Top-10 selection, rank-15 persistence buffer, 60-day Ledoit-Wolf covariance, shrinkage maximum-diversification risk anchor, 25% signal / 75% covariance-risk blend, 18% single-name cap, long-only construction, and a 1.25x hard exposure ceiling. They also verify expanding-window walk-forward evaluation over 2021–2026, modeled transaction costs, overall and yearly simulated results, and the six published research decisions concerning universe breadth, horizon/cadence, portfolio breadth, covariance, signal blending, and exposure governance.

## Planned routes

- `/`: institutional overview and the requested evidence sequence.
- `/rankings`: primary sortable/searchable ranking product surface with an accessible detail dialog.
- `/portfolio`: release-aligned portfolio integration status; holdings remain unavailable until a governed portfolio snapshot is exported.
- `/research`: research index.
- `/research/performance`: overall and yearly walk-forward evidence.
- `/research/experiments`: accepted/rejected/superseded/inconclusive archive derived only from governed decisions and artifacts.
- `/methodology`: locked configuration, supported explanations, and explicit documentation gaps.
- `/architecture`: interactive eight-stage system map with source paths and provenance.
- `/about`: project position and honest use of automation/AI infrastructure.
- `/candidates` and `/disclosures`: retained existing public research surfaces.
- GitHub remains an external link to the repository remote.

## New and refined components

- Native SVG Edge Glyph family: full lockup, symbol, compact mark, light/dark monochrome marks, and favicon/app icon.
- Responsive site header with current-route state, mobile body-scroll lock, Escape handling, initial focus, and focus restoration.
- Typed research adapter with runtime shape checks and explicit available/unavailable/error results.
- Research configuration strip, pipeline, provenance disclosure, evidence panels, and missing-artifact states.
- Ranking explorer with supported sorting/search, desktop sticky table, mobile compact rows, no-results state, and accessible detail dialog.
- Portfolio unavailable surface bound to the expected governed artifact contract.
- Methodology disclosures using native keyboard-operable details/summary controls.
- Interactive architecture modules using buttons and a single evidence panel, with keyboard and touch support.
- Route-level loading skeleton, parsing error recovery, and designed 404.

## Research-data contract

The website boundary supports:

- snapshot metadata: schema version, status, generated timestamp, signal/evaluation date, and live/simulated flags;
- model configuration: universe, horizon, cadence, breadth, buffer, covariance, risk anchor, blend, caps, and direction;
- rankings: rank, ticker, score, percentile, volatility, risk state, model configuration, selection band, and provenance;
- portfolio: snapshot date, holdings, weights, exposure, selection status, and optional risk contribution when a governed artifact exists;
- performance: evaluation period, return, volatility, Sharpe, Sortino, drawdown, exposure, turnover, transaction costs, and explicit simulation labels;
- experiments: hypothesis, result, evidence, decision, status, evaluation period, source artifact, commit, and update timestamp;
- limitations and provenance: source, artifact, model, portfolio, commit, generated timestamp, and update timestamp.

Changing research outputs are loaded through `web/src/lib/site-data.ts`; presentation components do not embed ranking or performance values. Data adapters return discriminated states so missing or malformed artifacts render deliberately.

## Known unavailable data

- No governed release-aligned current portfolio holdings/weights JSON exists. `results/policy_position_weights.csv` belongs to a different policy/run and is not used as the release portfolio.
- Ranking company names are not present in the governed ranking snapshot. Candidate company metadata is a different research universe/snapshot and is not joined speculatively.
- No release snapshot field verifies per-name conviction labels, expected return, current portfolio weight, per-position risk contribution, persistence/buffer membership, historical rank movement, or signal decomposition.
- No genuine live performance exists.
- No release-equity time series is included in the public contract, so the performance page does not draw an invented chart.
- The governed six-decision ledger does not separately encode an experiment status taxonomy beyond `locked`, `retained`, and `rejected`; the adapter maps only defensible public archive states and does not manufacture experiments.

## Decisions made to avoid fabricated metrics

- Top-10 rows are labeled as being in the current selection band, not as confirmed holdings.
- Company name cells render `Not provided` rather than joining unrelated or temporally inconsistent metadata.
- Portfolio renders a precise missing-artifact contract instead of deriving holdings from rankings or an incompatible policy CSV.
- Methodology explanations separate repository-supported rationale from documentation gaps.
- Performance is always labeled simulated walk-forward research and includes the model-selection-bias disclosure.
- Provenance exposes repository-relative source paths only; no private filesystem paths are rendered.

## Validation commands

From `web/`:

```bash
npm ci
npm run lint
npx tsc --noEmit
npm run validate:site
npm run build
npm run smoke
```

Repository regression checks, if public-site changes touch export contracts:

```bash
./venv/bin/python -m pytest -q tests/test_web_release_contract.py tests/test_website_snapshot_export.py tests/test_release_snapshot.py tests/test_release_rankings_snapshot.py tests/test_branding_consistency.py
```

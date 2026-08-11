# Salarium Public Product

This directory contains the production-facing Salarium 1.0 website. It is a Next.js application that presents committed research artifacts without claiming that the data is live or that simulated results are investment advice.

## Public routes

| Route | Purpose |
|---|---|
| `/` | Release overview, core mandate, latest committed ranks, and research decisions |
| `/rankings` | Searchable and sortable Liquid-500 ranking snapshot |
| `/candidates` | Evidence-governed broad-universe candidate explorer |
| `/architecture` | Locked Salarium 1.0 system architecture and governance chain |
| `/research` | Walk-forward evidence, yearly results, decision ledger, and limitations |
| `/about` | Project identity, purpose, and plain-English explanation |
| `/disclosures` | Research, data, execution, leverage, and advice boundaries |

## Local development

From `web/`:

```bash
npm ci
npm run dev
```

Open `http://localhost:3000`.

## Production release gate

```bash
npm run check
```

The command runs:

1. ESLint.
2. Static route, link, button, placeholder, and data-contract validation.
3. A full optimized Next.js build.
4. A production-server smoke test across every public route, data artifact, and 404 behavior.

## Data contracts

The site reads three committed JSON artifacts:

- `public/data/release_snapshot.json` — locked architecture, mandate results, yearly evidence, decision ledger, governance, and provenance.
- `public/data/release_rankings_snapshot.json` — top 25 names from the final 20D model’s latest committed Liquid-500 out-of-sample cross-section, with rank, score percentile, risk state, and provenance.
- `public/data/candidate_funnel_snapshot.json` — evidence-governed candidate research packet.

The public ranking artifact is regenerated from the governed 20D out-of-sample score stream, then the release artifact is rebuilt from committed research reports:

```bash
../venv/bin/python ../scripts/export_release_rankings.py
../venv/bin/python ../scripts/export_release_snapshot.py
```

## Deployment

The application is designed for Vercel with `web/` as the project root. Set `NEXT_PUBLIC_SITE_URL` to the canonical production URL so metadata, robots, sitemap, and social images resolve correctly.

After deployment, verify the actual public origin—not just the local build:

```bash
npm run check:deployment -- https://your-production-domain.example
```

The deployment checker opens every public route and data artifact, follows every rendered internal link, verifies the security headers, and confirms custom 404 behavior.

The site deliberately contains no brokerage integration, order routing, user accounts, or personalized portfolio recommendations.

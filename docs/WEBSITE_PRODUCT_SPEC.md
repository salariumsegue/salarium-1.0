# Salarium 1.0 Website Product Specification

## Product promise

The website must explain Salarium at two levels simultaneously:

1. a non-technical visitor should understand what the system does, why the research is differentiated, and why the risk disclosures matter;
2. a technical or institutional reviewer should be able to trace the displayed claims to committed data, source reports, code, and governance tests.

## Visual archetype

- dark-first and premium;
- black, white, green, and red only;
- restrained rather than “crypto casino” styling;
- dense enough to signal technical depth, but progressively disclosed;
- clear hierarchy, high contrast, keyboard focus, and responsive navigation;
- no decorative chart or metric without an explanatory purpose.

## Information architecture

| Route | Primary user question |
|---|---|
| Overview | What is Salarium and why should I care? |
| Rankings | What did the latest committed model cross-section rank highly? |
| Candidates | How does the broader research funnel collect and govern evidence? |
| Architecture | How does data become a governed portfolio research decision? |
| Research | Which experiments created the release architecture, and what failed? |
| About | Who built this, why, and what standards guide the project? |
| Disclosures | What must not be inferred from the research? |

## Non-negotiable interaction contract

- Every primary navigation item has a real route.
- Every button or link has a real destination or working client interaction.
- Mobile navigation is fully operable.
- Search, filter, sort, expand, and reset controls work without page reloads.
- The custom 404 page provides working recovery paths.
- Data links open the exact committed JSON artifacts used by the interface.
- There are no placeholder hash links, empty links, disabled controls, starter copy, TODOs, or “coming soon” surfaces.

## Evidence contract

- Release architecture: Liquid-500, 20D target, 10D rebalance, Top-10, rank-15 buffer, 60D Ledoit-Wolf covariance, 25% signal blend, 1.25x hard leverage cap.
- Historical results are labeled simulated.
- Ranking and candidate artifacts are labeled committed and not live. The ranking artifact exposes the top 25 names from the final 20D model’s latest Liquid-500 out-of-sample cross-section.
- The broad candidate plane is explicitly separated from the locked portfolio universe.
- Research decisions include rejected hypotheses and source-report provenance.
- Performance metrics never appear without visible caveats and a route to complete disclosures.

## Release automation

The website release is gated by:

1. Python snapshot-governance and product-contract tests;
2. tracked-file open-source audit;
3. ESLint;
4. Next.js production build;
5. static route/link/data validation;
6. production-server route and link smoke test;
7. clean Git branch and committed snapshot provenance.

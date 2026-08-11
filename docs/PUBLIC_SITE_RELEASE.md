# Salarium 1.0 Public Site Release Standard

## Product objective

The Salarium public site must communicate an institutional research process without becoming inaccessible to non-technical visitors. Every page should answer three questions:

1. What does the system do?
2. What evidence supports the claim?
3. What are the limits of that evidence?

The design vocabulary is intentionally constrained to black, white, green, and red. Green represents validated or constructive research evidence; red is reserved for risk, limitation, and failure states.

## Release routes

The release surface is fixed at:

- Overview
- Rankings
- Candidates
- Architecture
- Research
- About
- Disclosures

Every navigation item, call-to-action, footer link, raw-data link, and external source link must resolve. There are no placeholder buttons, disabled launch controls, empty sections, or “coming soon” pages in the release candidate.

## Data truthfulness

- Public ranking and candidate pages display committed snapshots, not streaming market data. The ranking page publishes the top 25 names from the final 20D model’s latest Liquid-500 out-of-sample cross-section.
- Simulated historical results are labeled as simulated.
- Rankings are relative model outputs, not price targets or trade instructions.
- Candidate packets are research-prioritization artifacts, not portfolio holdings.
- The leverage ceiling is a governance permission, not a return target.
- The site exposes snapshot dates, source reports, Git branch, and commit provenance.

## Accessibility and usability

- Responsive navigation is required on mobile and desktop.
- Every route includes the `main-content` skip-link target.
- Interactive controls have visible focus states and explicit labels.
- Motion respects `prefers-reduced-motion`.
- Tables remain scrollable on small screens.
- Technical explanations are paired with plain-English summaries.

## Automated release gates

A public-site change is not release-ready until all of the following pass:

```bash
python -m pytest -q
python scripts/open_source_audit.py
cd web
npm ci
npm run check
```

`npm run check` validates internal routes and buttons, scans for scaffold or placeholder copy, builds the production application, serves it locally, checks every route and data artifact, and verifies 404 behavior.

## Human release gate

Automation cannot judge the full visual experience. Before merging to `main`:

1. Inspect every route at desktop, tablet, and mobile widths.
2. Click every navigation link, CTA, data link, and external source link.
3. Confirm the production Vercel preview uses the expected release snapshot.
4. Confirm no page implies live trading, live performance, or personalized advice.
5. Verify the canonical production URL and social preview.
6. Review copy for accuracy, clarity, spelling, and consistent Salarium branding.

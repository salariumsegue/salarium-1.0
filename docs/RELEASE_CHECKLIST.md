# Salarium 1.0 Release Checklist

## Automated release blockers

- [ ] Full Python regression suite passes.
- [ ] Release snapshot schema and locked-architecture tests pass.
- [ ] Public product contract tests pass.
- [ ] Tracked-file open-source audit passes.
- [ ] Next.js lint passes.
- [ ] Next.js production build passes.
- [ ] Static site contract passes.
- [ ] Production route/link smoke test passes.
- [ ] Release snapshot is regenerated from committed research.
- [ ] Release branch is clean and pushed.

## Public-product completeness

- [ ] Overview, Rankings, Candidates, Architecture, Research, About, Disclosures, and custom 404 routes render.
- [ ] Desktop and mobile navigation reach every primary route.
- [ ] Every visible button and link has a valid destination or working interaction.
- [ ] Search, filter, sort, expand, reset, and mobile-menu interactions work.
- [ ] Ranking and candidate dates are labeled as committed artifacts, not live feeds.
- [ ] Rankings are generated from the final 20D model artifact and expose the source cross-section size, rank, score percentile, model configuration, and commit provenance.
- [ ] Broad candidate research is not confused with the locked Liquid-500 portfolio universe.
- [ ] Research page includes annual evidence, rejected hypotheses, and robustness.
- [ ] Performance, leverage, data, and investment-advice disclosures are visible.
- [ ] Metadata, sitemap, robots, manifest, icon, and not-found experience are production-specific.
- [ ] No local filesystem paths, starter copy, placeholders, or unfinished surfaces appear publicly.

## Human preview before merge to main

- [ ] Inspect the Vercel preview at desktop width.
- [ ] Inspect the Vercel preview at mobile width.
- [ ] Check keyboard focus and mobile menu behavior.
- [ ] Open every route and every footer/header link.
- [ ] Confirm ranking search/filter/sort behavior.
- [ ] Confirm candidate search/filter/sort/expand behavior.
- [ ] Review copy for factual alignment with the committed release snapshot.
- [ ] Confirm GitHub Actions Python and web jobs are green.
- [ ] Merge the validated web-production branch only after preview approval.

## After merge

- [ ] Confirm the production Vercel deployment is healthy.
- [ ] Run `npm run check:deployment -- https://<production-origin>` and require PASS.
- [ ] Tag `v1.0.0` only after production verification.
- [ ] Create GitHub Release notes from `docs/RELEASE_NOTES_1_0.md`.
- [ ] Capture final screenshots and a short product demo.
- [ ] Add the production website and repository to resume and LinkedIn materials.

# Salarium 1.0 Release Checklist

## Release blockers

- [ ] Python regression suite passes.
- [ ] Release snapshot governance tests pass.
- [ ] Next.js lint passes.
- [ ] Next.js production build passes.
- [ ] README reflects the current Liquid-500 / 20D / 10D / Top-10 architecture.
- [ ] Public website reads the release snapshot rather than only the legacy 5D policy summary.
- [ ] Website does not describe historical output as live trading performance.
- [ ] Research limitations and simulated-performance disclosure are visible.
- [ ] Latest committed rankings date is clearly labeled as a committed research snapshot.
- [ ] Release candidate branch is clean and pushed.

## Before merge to main

- [ ] Open the Vercel preview and check desktop/mobile layouts.
- [ ] Verify Overview, Rankings, Candidates, Architecture, and Research routes.
- [ ] Confirm no local paths, secrets, tokens, private data, or large generated artifacts are committed.
- [ ] Confirm GitHub Actions Python and web jobs are green.
- [ ] Create final release summary from committed report artifacts.
- [ ] Merge release branch to main only after the preview passes.

## After merge

- [ ] Confirm the production Vercel deployment is healthy.
- [ ] Tag `v1.0.0` only after production verification.
- [ ] Create GitHub Release notes from `docs/RELEASE_NOTES_1_0.md`.
- [ ] Add the production website and repository to resume/LinkedIn materials.

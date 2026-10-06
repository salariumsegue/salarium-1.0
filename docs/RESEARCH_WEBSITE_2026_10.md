# October 2026 research website

The homepage now prioritizes forward paper observations, with historical simulation in a separate section. Midnight blue surfaces, mint accents, and an orbital system diagram replace the previous homepage. Page headings describe their content rather than using generic paired slogans.

## Research features

- `/research/courtroom`: the 20% strategic oil sleeve, competing arguments, and a deterministic nine-gate verdict from committed acceptance results. Missing/non-true gates fail closed. The chronology inconsistency in the experiment metadata is disclosed. This release does not fabricate independent AI reviews or promote the hedge.
- `/replay`: four original rebalance snapshots imported from Git, including exact original bytes, hashes, recorded rankings, holdings and ledger events. Publication timestamp is distinct from rebalance date. Subsequent outcomes require a separate hindsight toggle that resets when the date changes. Raw feature matrices and complete covariance inputs are not archived.
- `/dependencies`: two editorial business themes backed by company source links. Tagged allocation is computed from current paper weights. Portfolio-wide correlation is explicitly separate from inferred themes. Unreviewed holdings stay visible; theme weights overlap.
- Homepage metric passports expose category, source, timestamp, model, commit, calculation and exclusions. `/api/evidence-bundle` downloads exact artifact bytes, SHA-256 hashes, archived decisions and 139 full-precision historical returns. Annualized return and historical drawdown reproduce from this stream. Current indicative NAV is preserved as a source observation; complete position marking inputs are not bundled.

## Ongoing publication

The scheduled forward-paper workflow appends new rebalance snapshots using `scripts/export_decision_archive.py --include-working`. Existing archive records remain unchanged. New records do not invent a publication commit before the Git commit exists. The narrowly scoped publication allowlist includes this archive; no model parameters or execution permissions changed.

The historical metric stream can be regenerated with `python scripts/export_research_return_stream.py`. Initial Git-history seeding uses `python scripts/export_decision_archive.py`; routine publication must use `--include-working` to preserve records.

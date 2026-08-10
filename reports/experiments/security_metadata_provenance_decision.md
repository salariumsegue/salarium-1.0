# Salarium Security Metadata Provenance Decision

## Decision

`data/processed/salarium_training_with_macro.csv`
is **not approved** as a point-in-time historical
sector source.

Classification:

`static_metadata_propagated_backward`

## Evidence

- The dataset contains 20 tickers and 1,599 dates
  from 2020-01-31 through 2026-06-11.
- Every ticker retains exactly one sector across
  the entire panel.
- There are zero observed sector transitions.
- The sector labels match
  `demo_stock_training_data.csv` for all 20
  overlapping tickers.
- `src/features/build_stock_training_data.py`
  assigns one sector value to every historical row
  for a ticker.
- `src/llm/merge_macro_features.py` carries the
  existing stock-row sector into the merged macro
  dataset.
- The generated historical CSV is not directly
  tracked in Git.

## Research Consequence

The sector field must not be used for:

- historical sector attribution;
- historical sector-neutral portfolio construction;
- historical sector exposure constraints;
- historical sector factor construction.

It may remain available for legacy display and
pipeline compatibility.

## Current Snapshot Metadata

The July 2026 Yahoo-derived files containing sector,
industry, and market capitalization remain approved
only for current/descriptive use.

## Requirement for Historical Approval

A future source must provide defensible as-of
semantics and provenance showing that each value was
available at or before the historical observation
date.

Until such a source exists, Salarium reports sector,
industry, size, value, and quality historical
attribution as unavailable rather than backfilling
present-day information.

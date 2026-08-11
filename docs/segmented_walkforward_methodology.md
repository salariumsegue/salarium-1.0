# Segmented Broad-Universe Walk-Forward Methodology

## Research Question

Does separating the broad point-in-time equity universe into independently trained liquidity tiers improve out-of-sample ranking quality and portfolio performance relative to:

1. the official liquid-500 model, and
2. the broad 2,000-name single-model experiment?

The experiment is motivated by the broad single-model result: widening the universe reduced ranking IC and Sharpe, suggesting that one feature-response function may not generalize uniformly across the entire liquidity distribution.

## What This Experiment Is

This is a **liquidity-tier-aware** model, not yet a true market-cap model.

The annual historical universe snapshots contain point-in-time `liquidity_rank`, based on trailing median dollar volume, but do not contain point-in-time shares outstanding or market capitalization. Calling these buckets “large cap,” “mid cap,” and “small cap” would therefore be methodologically inaccurate.

The governed tiers are:

| Tier | Annual point-in-time liquidity rank |
| --- | ---: |
| `tier_1_top500` | 1-500 |
| `tier_2_501_1000` | 501-1,000 |
| `tier_3_1001_2000` | 1,001-2,000 |

Earlier annual universes can contain fewer than 2,000 eligible securities. In those years, the third tier contains the remaining names.

## Controlled Experimental Design

To isolate the effect of segmentation, each tier initially uses the same:

- governed technical feature set,
- five-day forward-return target,
- annual walk-forward years,
- five-session purge,
- Random Forest model class,
- model hyperparameters,
- transaction-cost assumptions,
- approved portfolio policies, and
- market-regime risk controls.

The only primary model change is that each annual panel is divided into three point-in-time liquidity tiers and one independent model is fitted per tier.

## Score Recombination

Raw predictions from separately trained models are not directly comparable because their scales can differ.

For each test date and liquidity tier, raw predictions are converted to cross-sectional percentile scores. The percentile score becomes the governed combined `score` used by the existing portfolio evaluator.

This transformation:

- uses predictions only,
- does not use realized forward returns,
- preserves within-tier ordering, and
- places independent tier models on a common 0-to-1 scale.

Raw scores and within-tier z-scores are retained for diagnostics.

## Required Diagnostics

The experiment records:

- overall and annual policy performance,
- Spearman IC by liquidity tier,
- top-10 and bottom-10 returns by tier,
- tier-level long-short spread,
- global top-10 portfolio composition by tier,
- turnover and transaction costs,
- annualized return, Sharpe, excess Sharpe, and max drawdown,
- feature importance by tier and test year, and
- model/universe audit metadata.

## Decision Rule

The segmented system should not be promoted merely because it beats the broad single-model experiment. The relevant hurdle is the official liquid-500 benchmark.

Promotion requires a credible improvement in the risk-return frontier, supported by multiple years rather than one isolated regime. Ranking IC, turnover, drawdown, and transaction-cost-adjusted performance must be considered together.

## Important Limitation and Next Phase

Liquidity rank is correlated with company size but is not market capitalization. Highly traded smaller companies can enter the top liquidity tier, while less actively traded large companies can rank lower.

A true capitalization-aware extension requires annual point-in-time market capitalization constructed from:

1. the historical raw close at each annual cutoff, and
2. the latest SEC-reported shares outstanding whose conservative availability date is no later than that cutoff.

The segmented architecture is intentionally designed so that a future `market_cap_rank` mapping can replace the current `liquidity_rank` mapping without changing the downstream model, normalization, policy evaluation, or comparison contracts.

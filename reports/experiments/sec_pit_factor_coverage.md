# Salarium Point-in-Time Fundamental Factor Panel

## Status

- Rebalance dates: 276
- Securities: 500
- Factor rows: 135,022

## Point-in-Time Rule

SEC filing facts enter the factor panel only on or after their conservative `available_date`.

No statement-period end date is treated as an information availability date.

## Market Capitalization

Historical market capitalization uses raw `close`, not adjusted close, multiplied by the latest known SEC shares outstanding.

## Fundamental Factors

- Size: log market capitalization.
- Value: book-to-market and earnings yield.
- Quality: ROA, ROE, operating profitability.
- Secondary quality: gross profitability.
- Balance-sheet risk: leverage.

## Coverage

| Factor | Coverage | Median Names | Minimum Names | Latest Names |
| --- | ---: | ---: | ---: | ---: |
| market_cap | 84.9% | 415 | 390 | 433 |
| log_market_cap | 84.9% | 415 | 390 | 433 |
| book_to_market | 74.9% | 362 | 344 | 386 |
| earnings_yield | 74.3% | 361 | 329 | 394 |
| roa | 85.1% | 418 | 367 | 451 |
| roe | 78.9% | 383 | 344 | 421 |
| operating_profitability | 75.9% | 372 | 330 | 399 |
| gross_profitability | 42.5% | 208 | 185 | 225 |
| leverage | 70.8% | 348 | 299 | 372 |
| log_market_cap_z | 84.9% | 415 | 390 | 433 |
| book_to_market_z | 74.9% | 362 | 344 | 386 |
| earnings_yield_z | 74.3% | 361 | 329 | 394 |
| roa_z | 85.1% | 418 | 367 | 451 |
| roe_z | 78.9% | 383 | 344 | 421 |
| operating_profitability_z | 75.9% | 372 | 330 | 399 |
| gross_profitability_z | 42.5% | 208 | 185 | 225 |
| leverage_z | 70.8% | 348 | 299 | 372 |
| value_composite_z | 80.4% | 392 | 364 | 413 |
| quality_composite_z | 87.0% | 427 | 380 | 457 |

## Important Limitation

The current implementation uses latest-known annual fundamentals, not reconstructed trailing-twelve-month quarterly fundamentals.

Historical sector and industry classification remains unavailable and is not inferred from current metadata.

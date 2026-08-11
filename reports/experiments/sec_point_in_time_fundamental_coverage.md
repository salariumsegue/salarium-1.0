# SEC Point-in-Time Fundamental Coverage

## Methodology

Source: SEC EDGAR Company Facts XBRL API.

Facts are never made available using the financial statement period-end date.

The SEC `filed` date is treated as the disclosure date and Salarium applies an additional one-business-day conservative availability lag.

Minimum filing date retained: `2019-01-01`.

## Universe Coverage

- Securities audited: 500
- Normalized fact rows: 306448
- SEC ticker mappings: 499
- Successful company-facts requests: 499

## Fundamental Field Coverage

| Field | Securities | Coverage |
| --- | ---: | ---: |
| shares_outstanding | 434 | 86.8% |
| assets | 475 | 95.0% |
| liabilities | 374 | 74.8% |
| stockholders_equity | 475 | 95.0% |
| revenue | 455 | 91.0% |
| gross_profit | 250 | 50.0% |
| operating_income | 403 | 80.6% |
| net_income | 459 | 91.8% |

## Governance

This ledger is designed for point-in-time fundamental research. Historical values must be joined using `available_date`, never statement period end alone.

Historical sector and industry classification remains unavailable and blocked.

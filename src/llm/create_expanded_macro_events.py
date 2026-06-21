import csv
from pathlib import Path


OUTPUT_FILE = Path("data/raw/macro_events_expanded.csv")


events = [
    # 2020
    {
        "date": "2020-03-16",
        "event_type": "FOMC",
        "title": "Fed emergency rate cut and QE expansion",
        "actual": "Federal Reserve cut rates near zero and expanded asset purchases",
        "consensus": "Markets expected aggressive emergency easing",
        "prior": "Policy rates were above zero before emergency cuts",
        "market_reaction": "Equities remained under severe pressure. Treasury yields fell. Volatility stayed extremely elevated.",
        "text": "The Fed responded to COVID-driven financial stress with emergency easing, liquidity facilities, and asset purchases.",
    },
    {
        "date": "2020-04-03",
        "event_type": "Jobs Report",
        "title": "Payrolls collapse as COVID shutdowns hit labor market",
        "actual": "Payrolls fell sharply and unemployment surged",
        "consensus": "Markets expected severe labor-market damage",
        "prior": "Labor market had been strong before COVID shock",
        "market_reaction": "Equities remained volatile. Defensive assets outperformed. Risk appetite was fragile.",
        "text": "The labor market deteriorated rapidly as shutdowns spread across the economy.",
    },
    {
        "date": "2020-06-10",
        "event_type": "FOMC",
        "title": "Fed signals rates near zero for extended period",
        "actual": "Fed held rates near zero and emphasized ongoing support",
        "consensus": "Markets expected continued policy accommodation",
        "prior": "Emergency easing measures were already in place",
        "market_reaction": "Growth stocks and long-duration equities benefited from low-rate expectations.",
        "text": "The Fed reinforced a highly accommodative policy stance and signaled patience before tightening.",
    },
    {
        "date": "2020-11-09",
        "event_type": "Market Shock",
        "title": "Vaccine breakthrough boosts reopening expectations",
        "actual": "Positive vaccine news improved expectations for economic reopening",
        "consensus": "Markets had expected vaccine progress but timing was uncertain",
        "prior": "COVID restrictions continued to weigh on activity",
        "market_reaction": "Cyclicals, small caps, banks, energy, and reopening stocks surged. Stay-at-home technology lagged.",
        "text": "The vaccine announcement shifted the macro narrative toward reopening and stronger future growth.",
    },

    # 2021
    {
        "date": "2021-03-17",
        "event_type": "FOMC",
        "title": "Fed maintains dovish stance despite improving growth",
        "actual": "Fed kept policy highly accommodative",
        "consensus": "Markets expected rates to remain low",
        "prior": "Economic recovery was improving but policy remained easy",
        "market_reaction": "Risk assets remained supported. Growth and cyclicals both traded well.",
        "text": "The Fed emphasized patience and allowed the recovery to continue before tightening policy.",
    },
    {
        "date": "2021-05-12",
        "event_type": "CPI",
        "title": "Inflation surprise raises transitory debate",
        "actual": "Inflation came in hotter than expected",
        "consensus": "Markets expected inflation to rise but not as sharply",
        "prior": "Inflation had been accelerating from low pandemic levels",
        "market_reaction": "Treasury yields rose. High-duration technology stocks came under pressure.",
        "text": "A hotter inflation print intensified debate over whether inflation would be transitory or persistent.",
    },
    {
        "date": "2021-09-22",
        "event_type": "FOMC",
        "title": "Fed prepares market for tapering asset purchases",
        "actual": "Fed signaled tapering could begin soon",
        "consensus": "Markets expected taper discussion",
        "prior": "Asset purchases were still providing liquidity support",
        "market_reaction": "Markets digested the taper signal. Rate-sensitive stocks were mixed.",
        "text": "The Fed moved closer to reducing liquidity support as growth and inflation recovered.",
    },
    {
        "date": "2021-12-15",
        "event_type": "FOMC",
        "title": "Fed turns more hawkish as inflation pressure persists",
        "actual": "Fed accelerated tapering and signaled future rate hikes",
        "consensus": "Markets expected a hawkish shift",
        "prior": "Inflation had remained elevated for several months",
        "market_reaction": "Short-term yields rose. Growth stocks faced increasing rate pressure.",
        "text": "The policy narrative shifted away from emergency accommodation and toward inflation control.",
    },

    # 2022
    {
        "date": "2022-03-16",
        "event_type": "FOMC",
        "title": "Fed begins rate-hiking cycle",
        "actual": "Fed raised rates and signaled further tightening",
        "consensus": "Markets expected the first hike of the cycle",
        "prior": "Rates had been near zero",
        "market_reaction": "Yields moved higher. Rate-sensitive growth stocks remained pressured.",
        "text": "The Fed began tightening policy to fight inflation, marking a major liquidity regime shift.",
    },
    {
        "date": "2022-06-15",
        "event_type": "FOMC",
        "title": "Fed delivers aggressive inflation-fighting hike",
        "actual": "Fed raised rates aggressively",
        "consensus": "Markets expected a large hike after hot inflation data",
        "prior": "Inflation had surprised to the upside",
        "market_reaction": "Volatility remained elevated. Equities struggled under higher discount rates.",
        "text": "The Fed prioritized inflation control, tightening financial conditions and hurting long-duration assets.",
    },
    {
        "date": "2022-09-13",
        "event_type": "CPI",
        "title": "Hot CPI shocks markets",
        "actual": "Inflation came in hotter than expected",
        "consensus": "Markets expected inflation to moderate",
        "prior": "Investors hoped inflation had peaked",
        "market_reaction": "Equities sold off sharply. Treasury yields rose. Growth stocks underperformed.",
        "text": "The inflation surprise challenged the peak-inflation narrative and reinforced expectations for aggressive Fed tightening.",
    },
    {
        "date": "2022-11-10",
        "event_type": "CPI",
        "title": "Cooler CPI supports peak inflation narrative",
        "actual": "Inflation came in cooler than expected",
        "consensus": "Markets expected inflation to remain elevated",
        "prior": "Inflation had been persistently hot",
        "market_reaction": "Equities rallied sharply. Treasury yields fell. Growth stocks outperformed.",
        "text": "The cooler inflation print shifted expectations toward slower Fed tightening and improved liquidity conditions.",
    },

    # 2023
    {
        "date": "2023-03-13",
        "event_type": "Banking Stress",
        "title": "Regional banking stress drives flight to safety",
        "actual": "Bank failures and deposit stress raised financial stability concerns",
        "consensus": "Markets did not expect rapid banking-sector stress",
        "prior": "Financial conditions were already tight after rate hikes",
        "market_reaction": "Regional banks sold off. Treasury yields fell sharply. Defensive assets outperformed.",
        "text": "Banking stress introduced credit risk and raised the probability of tighter lending conditions.",
    },
    {
        "date": "2023-03-22",
        "event_type": "FOMC",
        "title": "Fed balances inflation fight with banking stress",
        "actual": "Fed raised rates but acknowledged banking-sector uncertainty",
        "consensus": "Markets were split due to banking stress",
        "prior": "Inflation remained elevated but financial stability risk increased",
        "market_reaction": "Markets were mixed as investors weighed tighter policy against credit stress.",
        "text": "The macro narrative became more complex, combining inflation pressure with financial stability concerns.",
    },
    {
        "date": "2023-07-12",
        "event_type": "CPI",
        "title": "Inflation cools more than expected",
        "actual": "CPI came in cooler than expected",
        "consensus": "Markets expected gradual disinflation",
        "prior": "Inflation had been trending lower",
        "market_reaction": "Equities rallied. Treasury yields declined. Growth stocks benefited.",
        "text": "The disinflation narrative strengthened and reduced pressure for additional aggressive rate hikes.",
    },
    {
        "date": "2023-11-14",
        "event_type": "CPI",
        "title": "Soft CPI boosts soft-landing hopes",
        "actual": "Inflation came in softer than expected",
        "consensus": "Markets expected inflation to continue easing",
        "prior": "Policy was restrictive but growth remained resilient",
        "market_reaction": "Stocks rallied broadly. Yields fell. Rate-sensitive sectors outperformed.",
        "text": "Softer inflation supported the idea that the Fed could stop hiking without causing a deep recession.",
    },

    # 2024
    {
        "date": "2024-01-31",
        "event_type": "FOMC",
        "title": "Fed pushes back on immediate rate cuts",
        "actual": "Fed held rates and emphasized need for more confidence on inflation",
        "consensus": "Markets expected guidance on future cuts",
        "prior": "Markets had priced meaningful easing expectations",
        "market_reaction": "Rate-cut expectations moved lower. Growth stocks were mixed.",
        "text": "The Fed pushed back against overly aggressive rate-cut expectations, keeping policy restrictive.",
    },
    {
        "date": "2024-04-10",
        "event_type": "CPI",
        "title": "Sticky inflation delays rate-cut expectations",
        "actual": "Inflation came in hotter than expected",
        "consensus": "Markets expected inflation progress",
        "prior": "Investors expected rate cuts later in the year",
        "market_reaction": "Yields rose. Equities sold off. High-duration sectors underperformed.",
        "text": "Sticky inflation challenged the disinflation narrative and pushed rate-cut expectations further out.",
    },
    {
        "date": "2024-07-11",
        "event_type": "CPI",
        "title": "Cooler inflation revives rate-cut hopes",
        "actual": "Inflation came in cooler than expected",
        "consensus": "Markets expected modest disinflation",
        "prior": "Inflation had remained sticky earlier in the year",
        "market_reaction": "Treasury yields fell. Rate-sensitive stocks improved. Broad risk appetite strengthened.",
        "text": "The cooler inflation report improved confidence that policy easing could begin if the trend continued.",
    },
    {
        "date": "2024-09-18",
        "event_type": "FOMC",
        "title": "Fed begins easing cycle",
        "actual": "Fed cut rates and signaled policy easing",
        "consensus": "Markets expected the start of rate cuts",
        "prior": "Policy had been restrictive",
        "market_reaction": "Equities reacted positively. Rate-sensitive sectors improved. Yields declined.",
        "text": "The start of the easing cycle shifted the liquidity impulse more supportive for risk assets.",
    },

    # 2025 seed events
    {
        "date": "2025-01-10",
        "event_type": "Consumer Confidence",
        "title": "Consumer confidence improves",
        "actual": "Consumer confidence index 112",
        "consensus": "Consumer confidence index 106",
        "prior": "Consumer confidence index 104",
        "market_reaction": "S&P 500 rose 0.5%. Consumer discretionary and travel stocks outperformed.",
        "text": "Household sentiment improved as inflation expectations eased and labor-market confidence remained firm.",
    },
    {
        "date": "2025-02-14",
        "event_type": "Retail Sales",
        "title": "Retail sales weaker than expected",
        "actual": "Retail sales -0.6% month-over-month",
        "consensus": "Retail sales -0.1% month-over-month",
        "prior": "Retail sales +0.4% month-over-month",
        "market_reaction": "Consumer discretionary stocks fell. Staples outperformed. Treasury yields declined slightly.",
        "text": "Consumer spending weakened sharply, raising concerns about demand softness.",
    },
    {
        "date": "2025-03-20",
        "event_type": "FOMC",
        "title": "Fed signals fewer cuts",
        "actual": "Fed held rates steady and signaled slower path of cuts",
        "consensus": "Fed expected to keep rate-cut path mostly unchanged",
        "prior": "Market expected more dovish tone",
        "market_reaction": "Nasdaq fell 1.4%. 2-year Treasury yield rose 12 bps. Dollar strengthened. Utilities and software underperformed.",
        "text": "Fed language emphasized sticky inflation and patience before easing policy.",
    },
    {
        "date": "2025-04-04",
        "event_type": "Jobs Report",
        "title": "Payrolls stronger than expected",
        "actual": "Nonfarm payrolls +275k",
        "consensus": "Nonfarm payrolls +200k",
        "prior": "Nonfarm payrolls +229k",
        "market_reaction": "S&P 500 rose 0.8%. 10-year yield rose 5 bps. Small caps outperformed. Cyclical sectors led.",
        "text": "Labor market strength surprised to the upside. Wage growth was stable and unemployment remained low.",
    },
    {
        "date": "2025-05-15",
        "event_type": "CPI",
        "title": "Core CPI hotter than expected",
        "actual": "Core CPI +0.4% month-over-month",
        "consensus": "Core CPI +0.3% month-over-month",
        "prior": "Core CPI +0.3% month-over-month",
        "market_reaction": "10-year Treasury yield rose 9 bps. Nasdaq initially sold off 1.1%, then recovered to close down only 0.2%. Regional banks outperformed. High-duration software lagged.",
        "text": "Inflation came in hotter than expected, mainly driven by services inflation. Shelter inflation remained sticky. Market-implied rate cut expectations declined.",
    },
]


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "date",
        "event_type",
        "title",
        "actual",
        "consensus",
        "prior",
        "market_reaction",
        "text",
    ]

    with OUTPUT_FILE.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(events)

    print(f"Saved {len(events)} expanded macro events to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

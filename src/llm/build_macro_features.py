import csv
from pathlib import Path

from src.llm.macro_interpreter import MacroInterpreter


INPUT_FILE = Path("data/raw/macro_events_expanded.csv")
OUTPUT_FILE = Path("data/processed/macro_llm_features.csv")


def main():
    interpreter = MacroInterpreter(model="llama3.2:1b")

    rows = []

    with INPUT_FILE.open("r", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            print(f"Analyzing {row['date']} - {row['event_type']} - {row['title']}")

            result = interpreter.analyze_event(row)
            output = result.model_dump()

            output["date"] = row["date"]
            output["title"] = row["title"]

            rows.append(output)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "date",
        "title",
        "event_type",
        "macro_tone",
        "macro_tone_score",
        "surprise_direction",
        "inflation_impulse",
        "growth_impulse",
        "rate_policy_impulse",
        "liquidity_impulse",
        "market_reaction_quality",
        "five_day_market_bias",
        "five_day_market_bias_score",
        "confidence",
        "reasoning_summary",
    ]

    with OUTPUT_FILE.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved macro LLM features to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

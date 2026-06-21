import csv
from pathlib import Path


INPUT_FILE = Path("data/processed/macro_llm_features.csv")
OUTPUT_FILE = Path("data/processed/macro_model_features.csv")


MAPS = {
    "macro_tone": {
        "bullish": 1,
        "neutral": 0,
        "bearish": -1,
    },
    "surprise_direction": {
        "better_than_expected": 1,
        "in_line": 0,
        "worse_than_expected": -1,
        "unclear": 0,
    },
    "inflation_impulse": {
        "lower": 1,
        "neutral": 0,
        "higher": -1,
    },
    "growth_impulse": {
        "stronger": 1,
        "neutral": 0,
        "weaker": -1,
    },
    "rate_policy_impulse": {
        "more_dovish": 1,
        "neutral": 0,
        "more_hawkish": -1,
    },
    "liquidity_impulse": {
        "easing": 1,
        "neutral": 0,
        "tightening": -1,
    },
    "market_reaction_quality": {
        "underreaction": 0.5,
        "efficient_reaction": 0,
        "overreaction": -0.5,
        "contradictory_reaction": 0,
        "unknown": 0,
    },
    "five_day_market_bias": {
        "bullish": 1,
        "neutral": 0,
        "bearish": -1,
    },
}


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def map_value(column, value):
    value = str(value).strip()
    return MAPS[column].get(value, 0)


def encode_row(row):
    macro_tone_num = map_value("macro_tone", row.get("macro_tone"))
    surprise_num = map_value("surprise_direction", row.get("surprise_direction"))
    inflation_num = map_value("inflation_impulse", row.get("inflation_impulse"))
    growth_num = map_value("growth_impulse", row.get("growth_impulse"))
    rate_policy_num = map_value("rate_policy_impulse", row.get("rate_policy_impulse"))
    liquidity_num = map_value("liquidity_impulse", row.get("liquidity_impulse"))
    reaction_quality_num = map_value("market_reaction_quality", row.get("market_reaction_quality"))
    five_day_bias_num = map_value("five_day_market_bias", row.get("five_day_market_bias"))

    macro_tone_score = safe_float(row.get("macro_tone_score"))
    five_day_market_bias_score = safe_float(row.get("five_day_market_bias_score"))
    confidence = safe_float(row.get("confidence"), 0.5)

    raw_signal = (
        0.25 * macro_tone_score
        + 0.25 * five_day_market_bias_score
        + 0.15 * rate_policy_num
        + 0.15 * liquidity_num
        + 0.10 * growth_num
        + 0.05 * surprise_num
        + 0.05 * reaction_quality_num
    )

    macro_signal_score = raw_signal * confidence

    return {
        "date": row.get("date"),
        "title": row.get("title"),
        "event_type": row.get("event_type"),

        "macro_tone_num": macro_tone_num,
        "surprise_num": surprise_num,
        "inflation_num": inflation_num,
        "growth_num": growth_num,
        "rate_policy_num": rate_policy_num,
        "liquidity_num": liquidity_num,
        "reaction_quality_num": reaction_quality_num,
        "five_day_bias_num": five_day_bias_num,

        "macro_tone_score": macro_tone_score,
        "five_day_market_bias_score": five_day_market_bias_score,
        "macro_confidence": confidence,
        "macro_signal_score": round(macro_signal_score, 4),
    }


def main():
    rows = []

    with INPUT_FILE.open("r", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            rows.append(encode_row(row))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "date",
        "title",
        "event_type",
        "macro_tone_num",
        "surprise_num",
        "inflation_num",
        "growth_num",
        "rate_policy_num",
        "liquidity_num",
        "reaction_quality_num",
        "five_day_bias_num",
        "macro_tone_score",
        "five_day_market_bias_score",
        "macro_confidence",
        "macro_signal_score",
    ]

    with OUTPUT_FILE.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved encoded macro model features to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

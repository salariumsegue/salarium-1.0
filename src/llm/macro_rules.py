from typing import Dict, Any


HAWKISH_FOMC_PHRASES = [
    "fewer cuts",
    "fewer rate cuts",
    "slower path of cuts",
    "higher for longer",
    "sticky inflation",
    "persistent inflation",
    "inflation remains elevated",
    "patience before easing",
    "patient before easing",
    "not ready to cut",
    "not confident",
    "restrictive policy",
    "tight policy",
    "rates higher",
    "delayed cuts",
    "cuts delayed",
]

DOVISH_FOMC_PHRASES = [
    "more cuts",
    "rate cuts likely",
    "cuts sooner",
    "easing soon",
    "inflation cooling",
    "inflation has eased",
    "labor market weakening",
    "downside risks",
    "policy easing",
    "dovish",
]


def contains_any(text: str, phrases: list[str]) -> bool:
    text = text.lower()
    return any(phrase in text for phrase in phrases)


def apply_macro_rules(parsed: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministic macro sanity-check layer.

    The local LLM gives the first interpretation.
    This layer fixes obvious macro contradictions.
    """

    event_type = str(event.get("event_type", "")).lower()

    combined_text = " ".join(
        [
            str(event.get("title", "")),
            str(event.get("actual", "")),
            str(event.get("consensus", "")),
            str(event.get("prior", "")),
            str(event.get("market_reaction", "")),
            str(event.get("text", "")),
        ]
    ).lower()

    # -----------------------------
    # FOMC hawkish correction
    # -----------------------------
    if "fomc" in event_type or "fed" in combined_text:
        hawkish_hit = contains_any(combined_text, HAWKISH_FOMC_PHRASES)
        dovish_hit = contains_any(combined_text, DOVISH_FOMC_PHRASES)

        if hawkish_hit and not dovish_hit:
            parsed["rate_policy_impulse"] = "more_hawkish"
            parsed["liquidity_impulse"] = "tightening"

            # If the model called this dovish, override the broad tone.
            if parsed.get("macro_tone") == "bullish":
                parsed["macro_tone"] = "neutral"

            if parsed.get("five_day_market_bias") == "bullish":
                parsed["five_day_market_bias"] = "neutral"

            # Push scores negative, but do not make them extreme.
            parsed["macro_tone_score"] = min(
                float(parsed.get("macro_tone_score", 0)),
                -0.2,
            )

            parsed["five_day_market_bias_score"] = min(
                float(parsed.get("five_day_market_bias_score", 0)),
                -0.2,
            )

            if parsed.get("surprise_direction") == "better_than_expected":
                parsed["surprise_direction"] = "worse_than_expected"

            reason = parsed.get("reasoning_summary", "")
            parsed["reasoning_summary"] = (
                reason
                + " Rule adjustment: FOMC language contained hawkish phrases such as fewer cuts, sticky inflation, or patience before easing."
            ).strip()

        elif dovish_hit and not hawkish_hit:
            parsed["rate_policy_impulse"] = "more_dovish"

            parsed["macro_tone_score"] = max(
                float(parsed.get("macro_tone_score", 0)),
                0.2,
            )

            parsed["five_day_market_bias_score"] = max(
                float(parsed.get("five_day_market_bias_score", 0)),
                0.1,
            )

            reason = parsed.get("reasoning_summary", "")
            parsed["reasoning_summary"] = (
                reason
                + " Rule adjustment: FOMC language contained dovish easing or cooling-inflation phrases."
            ).strip()

    return parsed
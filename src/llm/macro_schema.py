from pydantic import BaseModel, Field, ConfigDict
from typing import Literal


class MacroLLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str

    macro_tone: Literal["bullish", "neutral", "bearish"]
    macro_tone_score: float = Field(ge=-1, le=1)

    surprise_direction: Literal[
        "better_than_expected",
        "in_line",
        "worse_than_expected",
        "unclear",
    ]

    inflation_impulse: Literal["higher", "neutral", "lower"]
    growth_impulse: Literal["stronger", "neutral", "weaker"]
    rate_policy_impulse: Literal["more_hawkish", "neutral", "more_dovish"]
    liquidity_impulse: Literal["tightening", "neutral", "easing"]

    market_reaction_quality: Literal[
        "underreaction",
        "efficient_reaction",
        "overreaction",
        "contradictory_reaction",
        "unknown",
    ]

    five_day_market_bias: Literal["bullish", "neutral", "bearish"]
    five_day_market_bias_score: float = Field(ge=-1, le=1)

    confidence: float = Field(ge=0, le=1)
    reasoning_summary: str

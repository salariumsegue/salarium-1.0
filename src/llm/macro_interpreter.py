import json
from typing import Dict, Any

import requests

from src.llm.macro_schema import MacroLLMOutput
from src.llm.macro_prompt import SYSTEM_PROMPT, build_macro_user_prompt
from src.llm.macro_rules import apply_macro_rules


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_score(value, low=-1.0, high=1.0) -> float:
    """
    Converts local model outputs into valid Salarium score ranges.

    Examples:
    6 -> 0.6
    -6 -> -0.6
    0.7 -> 0.7
    75 -> 1.0 if score range is -1 to 1
    """
    try:
        v = float(value)
    except Exception:
        return 0.0

    if low == -1.0 and high == 1.0:
        if abs(v) > 1 and abs(v) <= 10:
            v = v / 10.0
        elif abs(v) > 10:
            v = 1.0 if v > 0 else -1.0

    return clamp(v, low, high)


def normalize_confidence(value) -> float:
    """
    Converts confidence into 0 to 1.

    Examples:
    7 -> 0.7
    70 -> 0.7
    0.7 -> 0.7
    """
    try:
        v = float(value)
    except Exception:
        return 0.5

    if v > 1 and v <= 10:
        v = v / 10.0
    elif v > 10 and v <= 100:
        v = v / 100.0

    return clamp(v, 0.0, 1.0)


def clean_output(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Makes local Ollama output compatible with the strict Pydantic schema.
    """

    parsed["macro_tone_score"] = normalize_score(
        parsed.get("macro_tone_score", 0.0),
        -1.0,
        1.0,
    )

    parsed["five_day_market_bias_score"] = normalize_score(
        parsed.get("five_day_market_bias_score", 0.0),
        -1.0,
        1.0,
    )

    parsed["confidence"] = normalize_confidence(
        parsed.get("confidence", 0.5)
    )

    return parsed


class MacroInterpreter:
    def __init__(
        self,
        model: str = "llama3.2:1b",
        base_url: str = "http://localhost:11434",
    ):
        self.model = model
        self.base_url = base_url

    def analyze_event(self, event: Dict[str, Any]) -> MacroLLMOutput:
        user_prompt = build_macro_user_prompt(event)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": user_prompt + """

Scoring rules:
- macro_tone_score must be between -1 and 1.
- five_day_market_bias_score must be between -1 and 1.
- confidence must be between 0 and 1.
- Do not use 1 to 10 scores.
- Do not use percentages.
""",
                },
            ],
            "stream": False,
            "format": MacroLLMOutput.model_json_schema(),
            "options": {"temperature": 0},
        }

        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=180,
        )

        response.raise_for_status()

        content = response.json()["message"]["content"]

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Ollama returned invalid JSON:\n{content}") from exc

        parsed = clean_output(parsed)
        parsed = apply_macro_rules(parsed, event)

        return MacroLLMOutput(**parsed)

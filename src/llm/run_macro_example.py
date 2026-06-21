from src.llm.macro_interpreter import MacroInterpreter


sample_event = {
    "date": "2025-05-15",
    "event_type": "CPI",
    "title": "April CPI Inflation Report",
    "actual": "Core CPI +0.4% month-over-month",
    "consensus": "Core CPI +0.3% month-over-month",
    "prior": "Core CPI +0.3% month-over-month",
    "market_reaction": """
    10-year Treasury yield rose 9 bps.
    Nasdaq initially sold off 1.1%, then recovered to close down only 0.2%.
    Regional banks outperformed.
    High-duration software lagged.
    """,
    "text": """
    Inflation came in hotter than expected, mainly driven by services inflation.
    Shelter inflation remained sticky.
    Market-implied rate cut expectations declined.
    """
}


if __name__ == "__main__":
    interpreter = MacroInterpreter()
    result = interpreter.analyze_event(sample_event)
    print(result.model_dump_json(indent=2))

from __future__ import annotations

ALPHA_BENCHMARK = "baseline_equal_weight"

RISK_MANAGED_CANDIDATE = (
    "turnover_buffer_inverse_volatility_risk_scaled"
)

POLICY_REGISTRY = {
    ALPHA_BENCHMARK: {
        "role": "alpha_benchmark",
        "status": "approved_research_benchmark",
        "deployment_approved": False,
    },
    RISK_MANAGED_CANDIDATE: {
        "role": "risk_managed_candidate",
        "status": "approved_research_candidate",
        "deployment_approved": False,
    },
    "turnover_buffer": {
        "role": "experimental",
        "status": "rejected_as_preferred_candidate",
        "deployment_approved": False,
    },
    "turnover_buffer_inverse_volatility": {
        "role": "experimental",
        "status": "rejected_as_preferred_candidate",
        "deployment_approved": False,
    },
}


def approved_research_policies() -> tuple[str, str]:
    return (
        ALPHA_BENCHMARK,
        RISK_MANAGED_CANDIDATE,
    )


def get_policy(name: str) -> dict:
    if name not in POLICY_REGISTRY:
        raise ValueError(
            f"Unknown portfolio policy: {name}"
        )

    return POLICY_REGISTRY[name].copy()

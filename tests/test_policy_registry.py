import pytest

from src.backtesting.policy_registry import (
    ALPHA_BENCHMARK,
    RISK_MANAGED_CANDIDATE,
    approved_research_policies,
    get_policy,
)


def test_approved_policy_roles() -> None:
    assert approved_research_policies() == (
        ALPHA_BENCHMARK,
        RISK_MANAGED_CANDIDATE,
    )


def test_alpha_policy_role() -> None:
    policy = get_policy(ALPHA_BENCHMARK)

    assert policy["role"] == "alpha_benchmark"
    assert policy["deployment_approved"] is False


def test_risk_policy_role() -> None:
    policy = get_policy(
        RISK_MANAGED_CANDIDATE
    )

    assert (
        policy["role"]
        == "risk_managed_candidate"
    )
    assert policy["deployment_approved"] is False


def test_unknown_policy_raises() -> None:
    with pytest.raises(ValueError):
        get_policy("unknown")

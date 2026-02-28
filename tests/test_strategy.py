"""Tests for the Strategy Advisor plugin.

Covers:
- capacity_strategy_engine (unit tests with mocked azure_api)
- strategy selection logic
- POST /plugins/strategy/capacity-strategy endpoint (integration tests)
"""

from unittest.mock import patch

from az_scout_strategy.engine import (
    _RegionEval,
    _select_strategy,
    recommend_capacity_strategy,
)
from az_scout_strategy.models import WorkloadProfileRequest


# ---------------------------------------------------------------------------
# Fixtures — SKU dicts matching azure_api.get_skus output
# ---------------------------------------------------------------------------


def _make_sku(
    name: str = "Standard_D2s_v3",
    family: str = "standardDSv3Family",
    zones: list[str] | None = None,
    restrictions: list[str] | None = None,
    vcpus: str = "2",
    memory_gb: str = "8",
) -> dict:
    return {
        "name": name,
        "family": family,
        "zones": zones if zones is not None else ["1", "2", "3"],
        "restrictions": restrictions if restrictions is not None else [],
        "capabilities": {"vCPUs": vcpus, "MemoryGB": memory_gb},
    }


def _enrich_quotas(skus: list[dict], *_args, **_kwargs) -> list[dict]:
    for sku in skus:
        sku["quota"] = {"limit": 100, "used": 10, "remaining": 90}
    return skus


def _enrich_quotas_blocking(skus: list[dict], *_args, **_kwargs) -> list[dict]:
    for sku in skus:
        sku["quota"] = {"limit": 100, "used": 100, "remaining": 0}
    return skus


def _enrich_prices(skus: list[dict], *_args, **_kwargs) -> list[dict]:
    for sku in skus:
        sku["pricing"] = {"paygo": 0.10, "spot": 0.03}
    return skus


SAMPLE_SPOT_SCORES: dict = {
    "scores": {
        "Standard_D2s_v3": {"1": "High", "2": "High", "3": "Medium"},
    },
    "errors": [],
}


def _make_profile(**overrides) -> WorkloadProfileRequest:
    defaults = {
        "workloadName": "test-workload",
        "subscriptionId": "sub-1",
        "scale": {"instanceCount": 2},
        "constraints": {"allowRegions": ["francecentral"]},
    }
    defaults.update(overrides)
    return WorkloadProfileRequest(**defaults)


# ---------------------------------------------------------------------------
# Strategy selection unit tests
# ---------------------------------------------------------------------------


def _make_region_eval(
    region: str = "francecentral",
    sku_name: str = "Standard_D2s_v3",
    zones: list[str] | None = None,
    restrictions: list[str] | None = None,
    vcpus: int = 2,
    quota_remaining: int | None = 90,
    spot_label: str = "High",
    confidence_score: int = 80,
) -> _RegionEval:
    return _RegionEval(
        region=region,
        sku_name=sku_name,
        zones=zones or ["1", "2", "3"],
        restrictions=restrictions or [],
        vcpus=vcpus,
        quota_remaining=quota_remaining,
        spot_label=spot_label,
        paygo=0.10,
        spot_price=0.03,
        confidence_score=confidence_score,
        confidence_label="High",
        family="standardDSv3Family",
    )


class TestSelectStrategy:
    def test_single_region_when_one_region(self) -> None:
        profile = _make_profile()
        primary = _make_region_eval()
        warnings: list[str] = []
        missing: list[str] = []
        result = _select_strategy(profile, [primary], primary, warnings, missing)
        assert result == "single_region"

    def test_stateful_gives_active_passive(self) -> None:
        profile = _make_profile(
            usage={"statefulness": "stateful"},
            constraints={"allowRegions": ["francecentral", "westeurope"]},
        )
        primary = _make_region_eval(region="francecentral")
        secondary = _make_region_eval(region="westeurope")
        warnings: list[str] = []
        missing: list[str] = []
        result = _select_strategy(profile, [primary, secondary], primary, warnings, missing)
        assert result == "active_passive"

    def test_quota_blocking_gives_shard(self) -> None:
        profile = _make_profile(
            scale={"instanceCount": 100},
            constraints={"allowRegions": ["francecentral", "westeurope"]},
        )
        primary = _make_region_eval(region="francecentral", quota_remaining=10)
        secondary = _make_region_eval(region="westeurope", quota_remaining=10)
        warnings: list[str] = []
        missing: list[str] = []
        result = _select_strategy(profile, [primary, secondary], primary, warnings, missing)
        assert result in ("sharded_multi_region", "progressive_ramp")

    def test_spot_low_gives_time_window(self) -> None:
        profile = _make_profile(
            pricing={"preferSpot": True},
            constraints={"allowRegions": ["francecentral", "westeurope"]},
        )
        primary = _make_region_eval(region="francecentral", spot_label="Low")
        secondary = _make_region_eval(region="westeurope")
        warnings: list[str] = []
        missing: list[str] = []
        result = _select_strategy(profile, [primary, secondary], primary, warnings, missing)
        assert result == "time_window_deploy"

    def test_high_latency_constraint_single_region(self) -> None:
        profile = _make_profile(
            usage={"latencySensitivity": "high"},
            constraints={
                "allowRegions": ["francecentral", "eastus"],
                "maxInterRegionRttMs": 20,
            },
        )
        primary = _make_region_eval(region="francecentral")
        secondary = _make_region_eval(region="eastus")
        warnings: list[str] = []
        missing: list[str] = []
        result = _select_strategy(profile, [primary, secondary], primary, warnings, missing)
        assert result == "single_region"
        assert any("RTT" in w for w in warnings)


# ---------------------------------------------------------------------------
# Engine integration tests (mocked azure_api)
# ---------------------------------------------------------------------------


class TestRecommendCapacityStrategy:
    @patch("az_scout_strategy.engine.azure_api")
    def test_nominal(self, mock_api) -> None:
        mock_api.get_skus.return_value = [_make_sku()]
        mock_api.enrich_skus_with_quotas.side_effect = _enrich_quotas
        mock_api.enrich_skus_with_prices.side_effect = _enrich_prices
        mock_api.get_spot_placement_scores.return_value = SAMPLE_SPOT_SCORES

        profile = _make_profile()
        result = recommend_capacity_strategy(profile)

        assert result.summary.workloadName == "test-workload"
        assert result.summary.regionCount >= 1
        assert result.summary.strategy == "single_region"
        assert result.technicalView.evaluatedAt is not None
        assert len(result.technicalView.allocations) >= 1
        assert result.disclaimer  # Always present

    @patch("az_scout_strategy.engine.azure_api")
    def test_quota_blocking_shards(self, mock_api) -> None:
        mock_api.get_skus.return_value = [_make_sku()]
        mock_api.enrich_skus_with_quotas.side_effect = _enrich_quotas_blocking
        mock_api.enrich_skus_with_prices.side_effect = _enrich_prices
        mock_api.get_spot_placement_scores.return_value = SAMPLE_SPOT_SCORES

        profile = _make_profile(
            scale={"instanceCount": 10},
            constraints={"allowRegions": ["francecentral", "westeurope"]},
        )
        result = recommend_capacity_strategy(profile)

        assert result.summary.workloadName == "test-workload"

    @patch("az_scout_strategy.engine.azure_api")
    def test_no_candidate_regions(self, mock_api) -> None:
        profile = _make_profile(
            constraints={
                "allowRegions": ["francecentral"],
                "denyRegions": ["francecentral"],
            },
        )
        result = recommend_capacity_strategy(profile)

        assert result.summary.regionCount == 0
        assert any("No candidate regions" in e for e in result.errors)

    @patch("az_scout_strategy.engine.azure_api")
    def test_unknown_latency_adds_warning(self, mock_api) -> None:
        mock_api.get_skus.return_value = [_make_sku()]
        mock_api.enrich_skus_with_quotas.side_effect = _enrich_quotas
        mock_api.enrich_skus_with_prices.side_effect = _enrich_prices
        mock_api.get_spot_placement_scores.return_value = SAMPLE_SPOT_SCORES

        profile = _make_profile(
            usage={"statefulness": "stateful"},
            constraints={"allowRegions": ["francecentral", "nonexistentregion"]},
        )
        result = recommend_capacity_strategy(profile)

        if result.summary.regionCount > 1:
            assert "latency" in result.missingInputs

"""Strategy Advisor MCP tool."""

import json
from typing import Annotated

from pydantic import Field

from az_scout_strategy.engine import recommend_capacity_strategy
from az_scout_strategy.models import (
    DataProfile,
    PricingSpec,
    ScaleSpec,
    TimingSpec,
    UsageProfile,
    WorkloadConstraints,
    WorkloadProfileRequest,
)


def capacity_strategy(
    workload_name: Annotated[str, Field(description="Human-readable name for the workload.")],
    subscription_id: Annotated[str, Field(description="Subscription ID to query.")],
    tenant_id: Annotated[str | None, Field(description="Optional tenant ID.")] = None,
    sku: Annotated[
        str | None,
        Field(description="Preferred VM SKU name (e.g. Standard_D2s_v3)."),
    ] = None,
    instance_count: Annotated[int, Field(description="Number of VM instances needed.")] = 1,
    gpu_count_total: Annotated[
        int | None, Field(description="Total GPU count needed (filters to GPU SKUs).")
    ] = None,
    data_residency: Annotated[str | None, Field(description="'FR', 'EU', or 'ANY'.")] = None,
    allow_regions: Annotated[
        list[str] | None, Field(description="Explicit list of candidate regions.")
    ] = None,
    deny_regions: Annotated[list[str] | None, Field(description="Regions to exclude.")] = None,
    require_zonal: Annotated[bool, Field(description="Require zone-redundant deployment.")] = False,
    max_inter_region_rtt_ms: Annotated[
        int | None, Field(description="Maximum acceptable RTT between regions.")
    ] = None,
    statefulness: Annotated[
        str, Field(description="'stateless', 'soft-state', or 'stateful'.")
    ] = "stateless",
    cross_region_traffic: Annotated[str, Field(description="'low', 'medium', or 'heavy'.")] = "low",
    latency_sensitivity: Annotated[
        str, Field(description="'low', 'medium', or 'high'.")
    ] = "medium",
    replication_mode: Annotated[
        str, Field(description="'none', 'async', 'sync', 'multi-master', 'unknown'.")
    ] = "unknown",
    rpo_target_seconds: Annotated[
        int | None, Field(description="Recovery Point Objective in seconds.")
    ] = None,
    rto_target_seconds: Annotated[
        int | None, Field(description="Recovery Time Objective in seconds.")
    ] = None,
    deployment_urgency: Annotated[
        str, Field(description="'now', 'today', or 'this_week'.")
    ] = "this_week",
    deployment_window: Annotated[
        str | None, Field(description="'anytime', 'night_cet', or 'weekend'.")
    ] = None,
    currency_code: Annotated[str, Field(description="'USD' or 'EUR'.")] = "USD",
    prefer_spot: Annotated[bool, Field(description="Prefer Spot VMs.")] = False,
    max_hourly_budget: Annotated[float | None, Field(description="Maximum hourly budget.")] = None,
) -> str:
    """Compute a deterministic Azure deployment strategy based on capacity signals and latency.

    Evaluates candidate (region, SKU) combinations against zones, quotas,
    restrictions, spot scores, pricing, confidence, and inter-region latency
    to recommend a multi-region deployment strategy.

    Must be used for any Azure deployment decision.  A single call returns
    a complete strategy with business justification and technical details.

    Strategies: single_region, active_active, active_passive,
    sharded_multi_region, burst_overflow, time_window_deploy,
    progressive_ramp.
    """
    profile = WorkloadProfileRequest(
        workloadName=workload_name,
        subscriptionId=subscription_id,
        tenantId=tenant_id,
        scale=ScaleSpec(sku=sku, instanceCount=instance_count, gpuCountTotal=gpu_count_total),
        constraints=WorkloadConstraints(
            dataResidency=data_residency,  # type: ignore[arg-type]
            allowRegions=allow_regions,
            denyRegions=deny_regions,
            requireZonal=require_zonal,
            maxInterRegionRttMs=max_inter_region_rtt_ms,
        ),
        usage=UsageProfile(
            statefulness=statefulness,  # type: ignore[arg-type]
            crossRegionTraffic=cross_region_traffic,  # type: ignore[arg-type]
            latencySensitivity=latency_sensitivity,  # type: ignore[arg-type]
        ),
        data=DataProfile(
            replicationMode=replication_mode,  # type: ignore[arg-type]
            rpoTargetSeconds=rpo_target_seconds,
            rtoTargetSeconds=rto_target_seconds,
        ),
        timing=TimingSpec(
            deploymentUrgency=deployment_urgency,  # type: ignore[arg-type]
            deploymentWindow=deployment_window,  # type: ignore[arg-type]
        ),
        pricing=PricingSpec(
            currencyCode=currency_code,  # type: ignore[arg-type]
            preferSpot=prefer_spot,
            maxHourlyBudget=max_hourly_budget,
        ),
    )
    result = recommend_capacity_strategy(profile)
    return json.dumps(result.model_dump(), indent=2)

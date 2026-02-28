"""Strategy Advisor API routes."""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from az_scout_strategy.engine import recommend_capacity_strategy
from az_scout_strategy.models import WorkloadProfileRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/capacity-strategy",
    summary="Compute a capacity deployment strategy",
)
async def capacity_strategy(body: WorkloadProfileRequest) -> JSONResponse:
    """Compute a deterministic Azure deployment strategy.

    Evaluates candidate regions and SKUs against capacity signals
    (zones, quotas, restrictions, spot scores, prices, confidence)
    and inter-region latency statistics to recommend a multi-region
    deployment strategy.

    A single call is sufficient for an agent to obtain a complete
    deployment recommendation.
    """
    try:
        result = recommend_capacity_strategy(body)
        return JSONResponse(result.model_dump())
    except Exception as exc:
        logger.exception("Failed to compute capacity strategy")
        return JSONResponse({"error": str(exc)}, status_code=500)

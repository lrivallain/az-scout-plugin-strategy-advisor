# az-scout-plugin-strategy-advisor

> **⚠️ Work in Progress** — This plugin is under active development. APIs, models, and behaviors may change without notice. It is not recommended for production use at this time.

[az-scout](https://az-scout.com) plugin for capacity deployment strategy recommendations.

## Features

- **UI tab** — Strategy Advisor form with subscription picker, workload constraints, and results rendering
- **API route** — `POST /plugins/strategy/capacity-strategy` to compute deployment strategies
- **MCP tool** — `capacity_strategy` tool for AI agents to obtain deployment recommendations
- **Strategy engine** — Evaluates (region, SKU) combinations against zones, quotas, restrictions, spot scores, pricing, confidence, and inter-region latency

## Strategies

The engine recommends one of: `single_region`, `active_active`, `active_passive`, `sharded_multi_region`, `burst_overflow`, `time_window_deploy`, `progressive_ramp`.

## Setup

```bash
uv pip install az-scout-plugin-strategy-advisor
az-scout  # plugin is auto-discovered
```

For development:

```bash
git clone https://github.com/az-scout/az-scout-plugin-strategy-advisor
cd az-scout-plugin-strategy-advisor
uv sync --group dev
uv pip install -e .
az-scout  # plugin is auto-discovered
```

## Structure

```
src/az_scout_strategy/
├── __init__.py          # Plugin class + module-level `plugin` instance
├── engine.py            # Capacity strategy computation engine
├── models.py            # Pydantic models (request/response)
├── routes.py            # FastAPI APIRouter (POST /capacity-strategy)
├── tools.py             # MCP tool function
└── static/
    ├── html/
    │   └── strategy-tab.html  # HTML fragment (fetched by JS at runtime)
    └── js/
        └── strategy-tab.js    # Tab UI logic
```

## Dependencies

This plugin depends on the following az-scout core modules:

- `az_scout.azure_api` — ARM API calls (SKUs, quotas, spot scores, prices)
- `az_scout.scoring.deployment_confidence` — Confidence scoring
- `az_scout.services._evaluation_helpers` — Shared evaluation utilities
- `az_scout.services.region_latency` — Inter-region latency data

## Quality checks

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest
```

## Copilot support

The `.github/copilot-instructions.md` file provides context to GitHub Copilot about
the plugin structure, conventions, and az-scout plugin API.

## License

[MIT](LICENSE.txt)

## Disclaimer

> **This tool is not affiliated with Microsoft.** All capacity, pricing, and availability information is indicative and not a guarantee of deployment success. Values are dynamic and may change between planning and actual deployment. Always validate in official Microsoft sources and in your target tenant/subscription.

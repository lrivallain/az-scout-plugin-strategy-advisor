# Copilot Instructions for az-scout-plugin-strategy-advisor

## Project overview

This is an **az-scout plugin** — a Python package that extends [az-scout](https://github.com/az-scout/az-scout) with the **Strategy Advisor** feature. It evaluates candidate (region, SKU) combinations against zones, quotas, restrictions, spot scores, pricing, confidence, and inter-region latency to recommend a multi-region deployment strategy.

## Tech stack

- **Backend:** Python 3.11+, FastAPI (APIRouter), az-scout plugin API
- **Frontend:** Vanilla JavaScript (no framework, no npm), CSS custom properties
- **Packaging:** hatchling + hatch-vcs, CalVer (`YYYY.MM.MICRO`), src-layout
- **Tools:** uv (package manager), ruff (lint + format), mypy, pytest

## Project structure

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

## Plugin API

The plugin class in `__init__.py` implements the `AzScoutPlugin` protocol:

| Method | Returns | Purpose |
|---|---|---|
| `get_router()` | `APIRouter \| None` | API route: POST /plugins/strategy/capacity-strategy |
| `get_mcp_tools()` | `list[Callable] \| None` | MCP tool: capacity_strategy |
| `get_static_dir()` | `Path \| None` | Static assets served at /plugins/strategy/static/ |
| `get_tabs()` | `list[TabDefinition] \| None` | Strategy Advisor UI tab |
| `get_chat_modes()` | `list[ChatMode] \| None` | None (no custom chat modes) |

## Code conventions

- **Python:** Type annotations on all functions. Follow ruff rules: `E, F, I, W, UP, B, SIM`. Line length: 100.
- **JavaScript:** Vanilla JS, `const`/`let` only, `camelCase` functions and variables.
- **HTML:** Use HTML fragment pattern — markup in `static/html/`, fetched at runtime by JS.

## Core dependencies

This plugin imports from az-scout core:

- `az_scout.azure_api` — ARM API calls (SKUs, quotas, spot scores, prices)
- `az_scout.scoring.deployment_confidence` — Confidence scoring
- `az_scout.services._evaluation_helpers` — Shared evaluation utilities (best_spot_label, etc.)
- `az_scout.services.region_latency` — Inter-region latency data

## Testing

- Mock `az_scout_strategy.engine.azure_api` (not the core module path)
- Use `unittest.mock.patch` for Azure API calls
- Never require live Azure calls in unit tests

## Quality checks

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest
```

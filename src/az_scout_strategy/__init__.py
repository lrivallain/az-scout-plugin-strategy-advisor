"""az-scout Strategy Advisor plugin.

Provides a capacity deployment strategy advisor that evaluates candidate
(region, SKU) combinations against zones, quotas, restrictions, spot scores,
pricing, confidence, and inter-region latency to recommend a multi-region
deployment strategy.
"""

from collections.abc import Callable
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any

from az_scout.plugin_api import ChatMode, TabDefinition
from fastapi import APIRouter

_STATIC_DIR = Path(__file__).parent / "static"

try:
    __version__ = _pkg_version("az-scout-plugin-strategy-advisor")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"


class StrategyAdvisorPlugin:
    """Strategy Advisor plugin for az-scout."""

    name = "strategy"
    version = __version__

    def get_router(self) -> APIRouter | None:
        """Return API routes mounted at /plugins/strategy/."""
        from az_scout_strategy.routes import router

        return router

    def get_mcp_tools(self) -> list[Callable[..., Any]] | None:
        """Return MCP tool functions."""
        from az_scout_strategy.tools import capacity_strategy

        return [capacity_strategy]

    def get_static_dir(self) -> Path | None:
        """Return path to static assets directory."""
        return _STATIC_DIR

    def get_tabs(self) -> list[TabDefinition] | None:
        """Return UI tab definitions."""
        return [
            TabDefinition(
                id="strategy",
                label="Strategy Advisor",
                icon="bi bi-compass",
                js_entry="js/strategy-tab.js",
            )
        ]

    def get_chat_modes(self) -> list[ChatMode] | None:
        """No custom chat modes."""
        return None


# Module-level instance — referenced by the entry point
plugin = StrategyAdvisorPlugin()

"""Pipeline Co-Pilot agent package.

ADK's discovery contract requires the package to expose `root_agent`. We import
it here so `adk web .`, `adk run pipeline_copilot`, and `adk api_server .` can
all find the agent.
"""

from .agent import root_agent

__all__ = ["root_agent"]

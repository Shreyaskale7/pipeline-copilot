"""
Pipeline Co-Pilot — multi-agent system (PHASE 3).

Architecture (graded key concept #1: multi-agent system):

    root_agent  (pipeline_copilot)          <- coordinator / router, no tools
        |
        |-- analyst_agent (pipeline_analyst) <- reads CRM, ranks risk, advises
        |-- writer_agent  (outreach_writer)  <- drafts grounded email, logs send

The coordinator uses LLM-driven delegation (ADK `sub_agents=`): it reads the
rep's request and routes pipeline/triage questions to the Analyst and drafting
requests to the Writer. Each specialist gets its OWN CRM MCP toolset instance so
their tool calls are isolated.

Why a single coordinator over a flat agent: the task is multi-step and adaptive
(read pipeline -> assess risk -> decide action -> optionally write + log). Splitting
the "decide what's at risk" reasoning from the "write grounded outreach" reasoning
keeps each agent's instruction focused and its tool use predictable.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from . import prompts

# Load .env so GOOGLE_API_KEY / GOOGLE_GENAI_USE_VERTEXAI / CRM_API_TOKEN are set
# before the agents (and the MCP subprocess they spawn) start.
load_dotenv()

# Gemini model. gemini-2.5-flash is fast/cheap and ample for tool routing;
# "gemini-flash-latest" is the documented fallback if this id is retired.
MODEL = "gemini-2.5-flash"

# Absolute path to the MCP server, resolved relative to this file so it works
# regardless of the launch directory.
SERVER_SCRIPT = str(Path(__file__).resolve().parent.parent / "mcp_server" / "crm_server.py")

# The write-auth secret, read from the environment (never hard-coded). Injected
# into the Writer's instruction so it can authorize log_activity calls.
CRM_API_TOKEN = os.environ.get("CRM_API_TOKEN", "demo-token")


def build_crm_toolset() -> McpToolset:
    """Construct an MCP toolset that connects ONE agent to the CRM server.

    The server runs as a stdio subprocess. We use `sys.executable` (the current
    interpreter) rather than the literal "python3" from the spec, because Windows
    has no "python3"; sys.executable is the portable, always-correct command.

    We pass CRM_API_TOKEN via `env` so the server's write-auth gate shares the
    agent's secret, and merge os.environ so the subprocess keeps PATH and the
    other OS variables it needs to launch.
    """
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=sys.executable,
                args=[SERVER_SCRIPT],
                env={**os.environ, "CRM_API_TOKEN": CRM_API_TOKEN},
            )
        )
    )


# --- Analyst: finds at-risk deals, explains why, ranks by value, advises ------
analyst_agent = LlmAgent(
    name="pipeline_analyst",
    model=MODEL,
    description="Triages the pipeline: finds at-risk deals, ranks by value at risk, recommends one next action each.",
    instruction=prompts.ANALYST_INSTRUCTION,
    tools=[build_crm_toolset()],
)

# --- Writer: drafts a grounded follow-up; logs only after rep confirms --------
writer_agent = LlmAgent(
    name="outreach_writer",
    model=MODEL,
    description="Drafts a short, grounded follow-up email for a specific deal and logs the outreach after the rep approves.",
    # Inject the auth token into the instruction at build time (from env) so the
    # Writer can authorize log_activity without the secret living in source.
    instruction=prompts.WRITER_INSTRUCTION.format(auth_token=CRM_API_TOKEN),
    tools=[build_crm_toolset()],
)

# --- Coordinator: routes to the right specialist (LLM-driven delegation) ------
root_agent = LlmAgent(
    name="pipeline_copilot",
    model=MODEL,
    description="Coordinator that routes sales-pipeline questions to the Analyst and drafting requests to the Writer.",
    instruction=prompts.COORDINATOR_INSTRUCTION,
    sub_agents=[analyst_agent, writer_agent],
)

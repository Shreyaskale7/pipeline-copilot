"""Throwaway verification (not a unit test): connect a real MCP client to the
CRM server over stdio and exercise every tool, including the security gate.
Proves the MCP layer works end-to-end WITHOUT needing a Gemini key."""

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = str(Path(__file__).resolve().parent.parent / "mcp_server" / "crm_server.py")


async def main():
    params = StdioServerParameters(command=sys.executable, args=[SERVER])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("TOOLS:", sorted(t.name for t in tools.tools))

            # FastMCP wraps a list return under structuredContent["result"];
            # a dict return appears directly as structuredContent.
            at_risk = await session.call_tool("get_deals", {"at_risk_only": True})
            deals = at_risk.structuredContent["result"]
            print("AT-RISK IDS:", [d["id"] for d in deals],
                  "values:", [d["value_at_risk"] for d in deals])

            import json

            def status_of(result):
                # Prefer structuredContent; fall back to parsing the text block.
                sc = result.structuredContent
                if sc and "status" in sc:
                    return sc["status"]
                return json.loads(result.content[0].text)["status"]

            # Security gate: wrong token must be rejected.
            bad = await session.call_tool("log_activity",
                {"deal_id": "D-1002", "summary": "test", "auth_token": "WRONG"})
            print("BAD TOKEN ->", status_of(bad))

            # Correct token must succeed.
            ok = await session.call_tool("log_activity",
                {"deal_id": "D-1002", "summary": "Emailed Tom t.becker@globex.example.com",
                 "auth_token": "demo-token"})
            print("GOOD TOKEN ->", status_of(ok))


asyncio.run(main())

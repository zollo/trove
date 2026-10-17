"""Smoke test: the FastAPI app builds and its schema generates.

Also guards the contract between the REST API and the MCP tools: every MCP
tool must have a REST operation with the same operationId.
"""
from __future__ import annotations

import asyncio


def test_app_and_openapi_build():
    from app.main import app

    assert app.title == "Trove"
    schema = app.openapi()
    paths = schema["paths"]
    assert "/api/health" in paths
    assert "/api/jobs" in paths
    assert "/api/candidates/{candidate_id}/resume" in paths
    assert "/mcp" not in paths


def test_every_mcp_tool_has_a_rest_operation():
    from app.main import app
    from app.mcp_server import mcp

    operation_ids = {
        op["operationId"] for path in app.openapi()["paths"].values() for op in path.values()
    }
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert names, "no MCP tools registered"
    assert names <= operation_ids, f"MCP tools without a REST twin: {names - operation_ids}"

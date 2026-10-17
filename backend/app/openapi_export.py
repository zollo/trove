"""Write the OpenAPI spec to a file.

    python -m app.openapi_export ../docs/openapi.json \
        [--mcp-tools ../docs/mcp-tools.json] [--version X.Y.Z]

CI checks that both files in docs/ are current, and attaches versioned copies
to every GitHub release.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--mcp-tools", type=Path, default=None, help="Also write MCP tools.")
    parser.add_argument("--version", default=None, help="Override info.version.")
    args = parser.parse_args()

    from app.main import app

    spec = app.openapi()
    if args.version:
        spec["info"]["version"] = args.version
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(spec, indent=2, sort_keys=False) + "\n")
    print(f"Wrote {args.output} ({len(spec['paths'])} paths)")

    if args.mcp_tools:
        from app.mcp_server import mcp

        tools = asyncio.run(mcp.list_tools())
        doc = {
            "server": "trove",
            "transport": "streamable-http",
            "path": "/mcp",
            "auth": "Authorization: Bearer <headhunter API key>",
            "tools": [t.model_dump(mode="json", by_alias=True, exclude_none=True) for t in tools],
        }
        args.mcp_tools.write_text(json.dumps(doc, indent=2) + "\n")
        print(f"Wrote {args.mcp_tools} ({len(tools)} tools)")


if __name__ == "__main__":
    main()

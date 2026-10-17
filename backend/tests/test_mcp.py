"""MCP endpoint tests: auth gate, tool discovery and an AI-headhunter workflow."""
from __future__ import annotations

import io
import json

MCP_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


def _key(client, hh) -> dict[str, str]:
    key = client.post("/api/api-keys", json={"name": "test"}, headers=hh).json()["key"]
    return {**MCP_HEADERS, "Authorization": f"Bearer {key}"}


def _rpc(client, headers, method, params=None, id_=1):
    body = {"jsonrpc": "2.0", "id": id_, "method": method}
    if params is not None:
        body["params"] = params
    resp = client.post("/mcp", headers=headers, content=json.dumps(body))
    assert resp.status_code == 200, resp.text
    return resp.json()


def _initialize(client, headers):
    return _rpc(
        client,
        headers,
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "pytest", "version": "1"},
        },
    )


def _call(client, headers, name, arguments):
    result = _rpc(client, headers, "tools/call", {"name": name, "arguments": arguments})["result"]
    return result


def test_mcp_requires_headhunter_key(client, candidate):
    _, cand_headers = candidate
    assert client.post("/mcp", headers=MCP_HEADERS, content="{}").status_code == 401
    resp = client.post("/mcp", headers={**MCP_HEADERS, **cand_headers}, content="{}")
    assert resp.status_code == 401


def test_mcp_tools_list(client, hh):
    headers = _key(client, hh)
    init = _initialize(client, headers)
    assert init["result"]["serverInfo"]["name"] == "trove"
    tools = _rpc(client, headers, "tools/list", {}, id_=2)["result"]["tools"]
    names = {t["name"] for t in tools}
    assert {
        "list_candidates",
        "get_candidate",
        "get_base_resume",
        "create_job",
        "update_job",
        "upload_optimized_resume",
    } <= names


def test_mcp_headhunter_workflow(client, hh, candidate):
    cid, cand_headers = candidate
    client.put(
        "/api/candidates/me/resume",
        files={"file": ("base.md", io.BytesIO(b"# Base resume\nKubernetes, Go"), "text/markdown")},
        headers=cand_headers,
    )
    headers = _key(client, hh)
    _initialize(client, headers)

    listed = _call(client, headers, "list_candidates", {})
    assert listed["structuredContent"]["result"][0]["id"] == cid

    resume = _call(client, headers, "get_base_resume", {"candidate_id": cid})
    assert "Kubernetes" in resume["structuredContent"]["text_content"]

    created = _call(
        client,
        headers,
        "create_job",
        {
            "candidate_id": cid,
            "title": "Staff SRE",
            "apply_url": "https://jobs.example.com/sre",
            "company": "Globex",
            "employment_type": "contract",
            "fit_score": 5,
        },
    )
    assert not created.get("isError"), created
    job_id = created["structuredContent"]["id"]

    dup = _call(
        client,
        headers,
        "create_job",
        {"candidate_id": cid, "title": "Staff SRE", "apply_url": "https://jobs.example.com/sre"},
    )
    assert dup["isError"] is True
    assert "already has a job" in dup["content"][0]["text"]

    bad = _call(
        client,
        headers,
        "create_job",
        {"candidate_id": cid, "title": "x", "apply_url": "https://x.example", "fit_score": 9},
    )
    assert bad["isError"] is True

    uploaded = _call(
        client,
        headers,
        "upload_optimized_resume",
        {"job_id": job_id, "filename": "globex", "content_text": "# Tailored"},
    )
    assert uploaded["structuredContent"]["filename"] == "globex.md"

    updated = _call(client, headers, "update_job", {"job_id": job_id, "status": "unavailable"})
    assert updated["structuredContent"]["status"] == "unavailable"

    # The candidate sees the posting and its tailored resume in the REST API.
    job = client.get(f"/api/jobs/{job_id}", headers=cand_headers).json()
    assert job["status"] == "unavailable"
    assert client.get(f"/api/jobs/{job_id}/resume", headers=cand_headers).content == b"# Tailored"

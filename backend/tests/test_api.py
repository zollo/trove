"""End-to-end REST API tests: auth, profiles, resumes and jobs."""
from __future__ import annotations

import base64
import io

from tests.conftest import login


def _job(candidate_id: str, **extra) -> dict:
    return {
        "candidate_id": candidate_id,
        "title": "Senior Platform Engineer",
        "apply_url": "https://example.com/jobs/123",
        "company": "Acme",
        "category": "Engineering",
        "employment_type": "permanent",
        "location": "Denver, CO",
        "work_mode": "hybrid",
        "compensation": "$170k-$190k",
        "schedule": "Mon-Fri, 9-5 MT",
        "fit_score": 4,
        "notes": "Strong Kubernetes overlap.",
        **extra,
    }


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/health/ready").json()["database"] is True


def test_login_and_me(client, hh):
    me = client.get("/api/auth/me", headers=hh).json()
    assert me["role"] == "headhunter"
    assert client.get("/api/auth/me").status_code == 401
    bad = client.post("/api/auth/login", json={"email": "hh@example.com", "password": "nope"})
    assert bad.status_code == 401


def test_register_duplicate(client, candidate):
    resp = client.post(
        "/api/auth/register", json={"email": "cand@example.com", "password": "another-pw"}
    )
    assert resp.status_code == 409


def test_profile_round_trip(client, candidate):
    cid, headers = candidate
    payload = {
        "headline": "Platform engineer",
        "desired_titles": ["SRE", " Platform Engineer ", "SRE"],
        "job_categories": ["Engineering"],
        "employment_types": ["permanent", "contract"],
        "locations": ["Denver, CO", "Remote US"],
        "work_modes": ["remote", "hybrid"],
        "salary_min": 160000,
        "salary_max": 200000,
        "salary_currency": "usd",
        "notes": "No on-call heavier than 1 week in 6.",
    }
    resp = client.put("/api/candidates/me/profile", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["desired_titles"] == ["SRE", "Platform Engineer"]
    assert body["salary_currency"] == "USD"

    detail = client.get(f"/api/candidates/{cid}", headers=headers).json()
    assert detail["profile"]["employment_types"] == ["permanent", "contract"]

    bad = dict(payload, salary_min=300000)
    assert client.put("/api/candidates/me/profile", json=bad, headers=headers).status_code == 422


def test_candidates_are_isolated(client, candidate, hh):
    _, cand_headers = candidate
    other = client.post(
        "/api/auth/register", json={"email": "other@example.com", "password": "other-pass"}
    ).json()
    other_id = other["user"]["id"]
    assert client.get(f"/api/candidates/{other_id}", headers=cand_headers).status_code == 403
    assert client.get("/api/candidates", headers=cand_headers).status_code == 403
    # Headhunters see everyone.
    listed = client.get("/api/candidates", headers=hh).json()
    assert {c["email"] for c in listed} == {"cand@example.com", "other@example.com"}


def test_base_resume_upload_download_and_text(client, candidate, hh):
    cid, headers = candidate
    content = b"# Jane Doe\n\nTen years of platform engineering."
    resp = client.put(
        "/api/candidates/me/resume",
        files={"file": ("jane.md", io.BytesIO(content), "text/markdown")},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["kind"] == "base_resume"

    dl = client.get(f"/api/candidates/{cid}/resume", headers=hh)
    assert dl.status_code == 200
    assert dl.content == content
    assert 'filename="jane.md"' in dl.headers["content-disposition"]

    text = client.get(
        f"/api/candidates/{cid}/resume/content?include_file=true", headers=hh
    ).json()
    assert "platform engineering" in text["text_content"]
    assert base64.b64decode(text["content_base64"]) == content

    # Replacing keeps a single base resume.
    client.put(
        "/api/candidates/me/resume",
        files={"file": ("jane.txt", io.BytesIO(b"v2"), "text/plain")},
        headers=headers,
    )
    summary = client.get("/api/candidates", headers=hh).json()[0]
    assert summary["has_base_resume"] is True
    assert client.get("/api/candidates/me/resume", headers=headers).content == b"v2"


def test_resume_rejects_unknown_type(client, candidate):
    _, headers = candidate
    resp = client.put(
        "/api/candidates/me/resume",
        files={"file": ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        headers=headers,
    )
    assert resp.status_code == 422


def test_job_lifecycle(client, candidate, hh):
    cid, cand_headers = candidate

    # Candidates cannot post jobs.
    assert client.post("/api/jobs", json=_job(cid), headers=cand_headers).status_code == 403

    resp = client.post("/api/jobs", json=_job(cid), headers=hh)
    assert resp.status_code == 201, resp.text
    job = resp.json()
    assert job["status"] == "new"
    assert job["date_found"]  # defaulted to today

    # Duplicate apply_url for the same candidate is rejected.
    assert client.post("/api/jobs", json=_job(cid), headers=hh).status_code == 409
    # Fit score is bounded.
    bad = _job(cid, apply_url="https://example.com/2", fit_score=6)
    assert client.post("/api/jobs", json=bad, headers=hh).status_code == 422

    # Candidate sees it and tracks their application...
    mine = client.get("/api/jobs", headers=cand_headers).json()
    assert [j["id"] for j in mine] == [job["id"]]
    resp = client.patch(
        f"/api/jobs/{job['id']}", json={"status": "applied", "notes": "Applied 10/17"},
        headers=cand_headers,
    )
    assert resp.status_code == 200 and resp.json()["status"] == "applied"
    # ...but cannot edit headhunter fields.
    resp = client.patch(f"/api/jobs/{job['id']}", json={"fit_score": 5}, headers=cand_headers)
    assert resp.status_code == 403

    # Headhunter marks it expired; filters work.
    client.patch(f"/api/jobs/{job['id']}", json={"status": "expired"}, headers=hh)
    expired = client.get(f"/api/jobs?candidate_id={cid}&status=expired", headers=hh).json()
    assert len(expired) == 1
    assert client.get("/api/jobs?q=acme", headers=hh).json()[0]["company"] == "Acme"
    assert client.get("/api/jobs?q=nomatch", headers=hh).json() == []

    options = client.get("/api/jobs/options", headers=cand_headers).json()
    assert options["categories"] == ["Engineering"]
    assert {"value": "expired", "label": "Expired"} in options["statuses"]

    assert client.delete(f"/api/jobs/{job['id']}", headers=cand_headers).status_code == 403
    assert client.delete(f"/api/jobs/{job['id']}", headers=hh).status_code == 204
    assert client.get(f"/api/jobs/{job['id']}", headers=hh).status_code == 404


def test_optimized_resume_per_job(client, candidate, hh):
    cid, cand_headers = candidate
    job = client.post("/api/jobs", json=_job(cid), headers=hh).json()

    resp = client.put(
        f"/api/jobs/{job['id']}/resume/content",
        json={"filename": "acme-resume", "content_text": "# Tailored for Acme"},
        headers=hh,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["filename"] == "acme-resume.md"

    fetched = client.get(f"/api/jobs/{job['id']}", headers=cand_headers).json()
    assert fetched["optimized_resume"]["filename"] == "acme-resume.md"
    dl = client.get(f"/api/jobs/{job['id']}/resume", headers=cand_headers)
    assert dl.content == b"# Tailored for Acme"

    # Multipart upload replaces it; candidates cannot upload.
    resp = client.put(
        f"/api/jobs/{job['id']}/resume",
        files={"file": ("acme.txt", io.BytesIO(b"v2"), "text/plain")},
        headers=cand_headers,
    )
    assert resp.status_code == 403
    client.put(
        f"/api/jobs/{job['id']}/resume",
        files={"file": ("acme.txt", io.BytesIO(b"v2"), "text/plain")},
        headers=hh,
    )
    assert client.get(f"/api/jobs/{job['id']}/resume", headers=hh).content == b"v2"


def test_api_keys(client, hh, candidate):
    _, cand_headers = candidate
    assert client.post("/api/api-keys", json={"name": "x"}, headers=cand_headers).status_code == 403

    created = client.post("/api/api-keys", json={"name": "Claude"}, headers=hh).json()
    key = created["key"]
    assert key.startswith("trove_")
    key_headers = {"Authorization": f"Bearer {key}"}
    assert client.get("/api/auth/me", headers=key_headers).json()["role"] == "headhunter"

    listed = client.get("/api/api-keys", headers=hh).json()
    assert listed[0]["last_used_at"] is not None
    assert "key" not in listed[0]

    assert client.delete(f"/api/api-keys/{created['id']}", headers=hh).status_code == 204
    assert client.get("/api/auth/me", headers=key_headers).status_code == 401


def test_headhunter_manages_users(client, hh):
    resp = client.post(
        "/api/users",
        json={"email": "hh2@example.com", "password": "second-hunter", "role": "headhunter"},
        headers=hh,
    )
    assert resp.status_code == 201
    login(client, "hh2@example.com", "second-hunter")
    uid = resp.json()["id"]
    client.patch(f"/api/users/{uid}", json={"is_active": False}, headers=hh)
    bad = client.post(
        "/api/auth/login", json={"email": "hh2@example.com", "password": "second-hunter"}
    )
    assert bad.status_code == 401

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import type { CandidateSummary } from "../../types";

export default function Candidates() {
  const [candidates, setCandidates] = useState<CandidateSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    api
      .get<CandidateSummary[]>("/api/candidates")
      .then(setCandidates)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load"));
  }, []);

  const needle = q.trim().toLowerCase();
  const visible = (candidates ?? []).filter(
    (c) => !needle || `${c.display_name} ${c.email} ${c.headline}`.toLowerCase().includes(needle),
  );

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Candidates</h1>
          <p className="subtitle" style={{ margin: 0 }}>
            The people you're finding jobs for.
          </p>
        </div>
        <Link className="btn secondary" to="/settings#users">
          Add candidate
        </Link>
      </div>
      {error && <div className="alert error">{error}</div>}
      {!candidates && !error && <p className="muted">Loading…</p>}
      {candidates && candidates.length > 0 && (
        <input
          type="search"
          placeholder="Search candidates…"
          aria-label="Search candidates"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          style={{ marginBottom: 12 }}
        />
      )}
      {candidates && candidates.length === 0 && (
        <div className="empty">
          No candidates yet. They can register themselves, or you can add them in Settings.
        </div>
      )}
      <div className="list">
        {visible.map((c) => (
          <Link key={c.id} to={`/candidates/${c.id}`} className="item">
            <div className="top">
              <div style={{ minWidth: 0 }}>
                <div className="title">{c.display_name}</div>
                <div className="company">{c.headline || c.email}</div>
              </div>
              <span className="badge st-new">{c.open_job_count} open</span>
            </div>
            <div className="meta">
              <span>{c.job_count} jobs total</span>
              <span>{c.has_base_resume ? "📄 Resume on file" : "⚠️ No resume yet"}</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

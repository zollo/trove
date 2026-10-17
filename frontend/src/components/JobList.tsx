import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { EMPLOYMENT_LABELS, STATUS_GROUPS, WORK_MODE_LABELS, formatDate } from "../lib/format";
import type { Job } from "../types";
import FitStars from "./FitStars";
import StatusBadge from "./StatusBadge";

type Sort = "date" | "fit";

// Filterable list of jobs. `candidateId` narrows a headhunter's view to one candidate.
export default function JobList({
  candidateId,
  showCandidate = false,
}: {
  candidateId?: string;
  showCandidate?: boolean;
}) {
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [group, setGroup] = useState("open");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<Sort>("date");

  useEffect(() => {
    const qs = candidateId ? `?candidate_id=${encodeURIComponent(candidateId)}` : "";
    api
      .get<Job[]>(`/api/jobs${qs}`)
      .then(setJobs)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load jobs"));
  }, [candidateId]);

  const visible = useMemo(() => {
    if (!jobs) return [];
    const statuses = STATUS_GROUPS.find((g) => g.key === group)?.statuses;
    const needle = q.trim().toLowerCase();
    const filtered = jobs.filter(
      (j) =>
        (!statuses || statuses.includes(j.status)) &&
        (!needle ||
          [j.title, j.company, j.location, j.category, j.candidate_name]
            .join(" ")
            .toLowerCase()
            .includes(needle)),
    );
    if (sort === "fit") {
      filtered.sort((a, b) => (b.fit_score ?? 0) - (a.fit_score ?? 0));
    }
    return filtered;
  }, [jobs, group, q, sort]);

  const counts = useMemo(() => {
    const out: Record<string, number> = {};
    for (const g of STATUS_GROUPS) {
      out[g.key] = (jobs ?? []).filter((j) => !g.statuses || g.statuses.includes(j.status)).length;
    }
    return out;
  }, [jobs]);

  if (error) return <div className="alert error">{error}</div>;
  if (!jobs) return <p className="muted">Loading jobs…</p>;

  return (
    <>
      <div className="filters" role="tablist">
        {STATUS_GROUPS.map((g) => (
          <button
            key={g.key}
            type="button"
            role="tab"
            aria-selected={group === g.key}
            className={`pill${group === g.key ? " active" : ""}`}
            onClick={() => setGroup(g.key)}
          >
            {g.label} {counts[g.key] ? `· ${counts[g.key]}` : ""}
          </button>
        ))}
      </div>
      <div className="row" style={{ marginBottom: 12, flexWrap: "nowrap" }}>
        <input
          type="search"
          placeholder="Search title, company, location…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="Search jobs"
        />
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as Sort)}
          aria-label="Sort"
          style={{ width: "auto" }}
        >
          <option value="date">Newest</option>
          <option value="fit">Best fit</option>
        </select>
      </div>

      {visible.length === 0 ? (
        <div className="empty">
          {jobs.length === 0 ? "No jobs have been posted yet." : "No jobs match this filter."}
        </div>
      ) : (
        <div className="list">
          {visible.map((j) => (
            <Link key={j.id} to={`/jobs/${j.id}`} className="item">
              <div className="top">
                <div style={{ minWidth: 0 }}>
                  <div className="title">{j.title}</div>
                  <div className="company">
                    {[j.company, showCandidate && j.candidate_name ? `for ${j.candidate_name}` : ""]
                      .filter(Boolean)
                      .join(" · ")}
                  </div>
                </div>
                <StatusBadge status={j.status} />
              </div>
              <div className="meta">
                {j.location && <span>📍 {j.location}</span>}
                {j.work_mode && <span>{WORK_MODE_LABELS[j.work_mode]}</span>}
                {j.employment_type && <span>{EMPLOYMENT_LABELS[j.employment_type]}</span>}
                {j.compensation && <span>💰 {j.compensation}</span>}
                <span>Found {formatDate(j.date_found)}</span>
                <FitStars score={j.fit_score} />
                {j.optimized_resume && <span>📄 Tailored resume</span>}
              </div>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}

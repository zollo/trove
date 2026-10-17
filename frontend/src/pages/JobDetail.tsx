import { useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import FileBox from "../components/FileBox";
import FitStars from "../components/FitStars";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../context/AuthContext";
import {
  EMPLOYMENT_LABELS,
  STATUSES,
  STATUS_LABELS,
  WORK_MODE_LABELS,
  formatDate,
} from "../lib/format";
import type { Job, JobStatus } from "../types";

export default function JobDetail() {
  const { id } = useParams();
  const { isHeadhunter } = useAuth();
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .get<Job>(`/api/jobs/${id}`)
      .then((j) => {
        setJob(j);
        setNotes(j.notes);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load job"));
  }, [id]);

  const patch = async (body: Partial<Job>, message: string) => {
    setError(null);
    setSaved(null);
    setBusy(true);
    try {
      const updated = await api.patch<Job>(`/api/jobs/${id}`, body);
      setJob(updated);
      // Keep an unsaved notes draft when only the status changed.
      if ("notes" in body) setNotes(updated.notes);
      setSaved(message);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!job || !confirm(`Delete "${job.title}"? This cannot be undone.`)) return;
    try {
      await api.del(`/api/jobs/${id}`);
      navigate(-1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed");
    }
  };

  if (error && !job) {
    return (
      <div className="page narrow">
        <div className="alert error">{error}</div>
      </div>
    );
  }
  if (!job) return <div className="page narrow muted">Loading…</div>;

  const closed = job.status === "expired" || job.status === "unavailable";

  return (
    <div className="page narrow">
      <button className="btn ghost" onClick={() => navigate(-1)} style={{ marginBottom: 8 }}>
        ← Back
      </button>
      <div className="page-head">
        <div>
          <h1>{job.title}</h1>
          <div className="muted">
            {job.company}
            {isHeadhunter && job.candidate_name && (
              <>
                {job.company ? " · " : ""}for{" "}
                <Link to={`/candidates/${job.candidate_id}`}>{job.candidate_name}</Link>
              </>
            )}
          </div>
        </div>
        <StatusBadge status={job.status} />
      </div>

      {error && <div className="alert error">{error}</div>}
      {saved && <div className="alert success">{saved}</div>}
      {closed && (
        <div className="alert info">
          This posting is marked {STATUS_LABELS[job.status].toLowerCase()}.
        </div>
      )}

      <div className="row" style={{ marginBottom: 16 }}>
        <a className="btn" href={job.apply_url} target="_blank" rel="noopener noreferrer">
          Apply ↗
        </a>
        {isHeadhunter && (
          <>
            <Link className="btn secondary" to={`/jobs/${job.id}/edit`}>
              Edit
            </Link>
            <button className="btn danger" onClick={remove}>
              Delete
            </button>
          </>
        )}
      </div>

      <div className="card">
        <div className="field" style={{ marginBottom: 0 }}>
          <label htmlFor="status">Status</label>
          <select
            id="status"
            value={job.status}
            disabled={busy}
            onChange={(e) =>
              void patch({ status: e.target.value as JobStatus }, "Status updated.")
            }
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="card">
        <h2>Tailored resume</h2>
        <p className="muted small" style={{ marginTop: -6 }}>
          A version of your resume rewritten for this specific job. Use it when you apply.
        </p>
        <FileBox
          doc={job.optimized_resume}
          path={`/api/jobs/${job.id}/resume`}
          canUpload={isHeadhunter}
          emptyText={isHeadhunter ? "No tailored resume yet." : "Not available yet."}
          onChange={(doc) => setJob({ ...job, optimized_resume: doc })}
        />
      </div>

      <div className="card">
        <h2>Details</h2>
        <dl className="facts">
          <Fact label="Job fit">
            {job.fit_score ? <FitStars score={job.fit_score} /> : "—"}
          </Fact>
          <Fact label="Category">{job.category || "—"}</Fact>
          <Fact label="Employment type">
            {job.employment_type ? EMPLOYMENT_LABELS[job.employment_type] : "—"}
          </Fact>
          <Fact label="Location">
            {[job.location, job.work_mode ? WORK_MODE_LABELS[job.work_mode] : ""]
              .filter(Boolean)
              .join(" · ") || "—"}
          </Fact>
          <Fact label="Compensation">{job.compensation || "—"}</Fact>
          <Fact label="Shift / schedule">{job.schedule || "—"}</Fact>
          <Fact label="Date found">{formatDate(job.date_found)}</Fact>
          <Fact label="Apply link">
            <a href={job.apply_url} target="_blank" rel="noopener noreferrer">
              {job.apply_url}
            </a>
          </Fact>
        </dl>
      </div>

      <div className="card">
        <h2>Notes</h2>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Why it fits, who you spoke to, follow-ups…"
          aria-label="Notes"
        />
        <div className="row" style={{ marginTop: 10 }}>
          <button
            className="btn"
            disabled={busy || notes === job.notes}
            onClick={() => void patch({ notes }, "Notes saved.")}
          >
            Save notes
          </button>
        </div>
      </div>
    </div>
  );
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  );
}

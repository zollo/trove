import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import FileBox from "../../components/FileBox";
import JobList from "../../components/JobList";
import { EMPLOYMENT_LABELS, WORK_MODE_LABELS, formatSalary } from "../../lib/format";
import type { CandidateDetail } from "../../types";

export default function CandidateView() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<CandidateDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<CandidateDetail>(`/api/candidates/${id}`)
      .then(setDetail)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load"));
  }, [id]);

  if (error) {
    return (
      <div className="page">
        <div className="alert error">{error}</div>
      </div>
    );
  }
  if (!detail) return <div className="page muted">Loading…</div>;
  const p = detail.profile;
  const salary = formatSalary(p);

  return (
    <div className="page">
      <button className="btn ghost" onClick={() => navigate(-1)} style={{ marginBottom: 8 }}>
        ← Back
      </button>
      <div className="page-head">
        <div>
          <h1>{detail.display_name}</h1>
          <div className="muted">{p.headline || detail.email}</div>
        </div>
        <Link className="btn" to={`/jobs/new?candidate=${detail.id}`}>
          Add job
        </Link>
      </div>

      <div className="grid two">
        <div className="card" style={{ marginTop: 0 }}>
          <h2>Search preferences</h2>
          <dl className="facts">
            <Pref label="Titles" values={p.desired_titles} />
            <Pref label="Categories" values={p.job_categories} />
            <Pref
              label="Employment"
              values={p.employment_types.map((t) => EMPLOYMENT_LABELS[t])}
            />
            <Pref
              label="Locations"
              values={[
                ...p.locations,
                ...p.work_modes.map((m) => WORK_MODE_LABELS[m]),
                ...(p.willing_to_relocate ? ["Will relocate"] : []),
              ]}
            />
            <div>
              <dt>Salary</dt>
              <dd>{salary || "—"}</dd>
            </div>
            <div>
              <dt>Email</dt>
              <dd>
                <a href={`mailto:${detail.email}`}>{detail.email}</a>
              </dd>
            </div>
          </dl>
          {p.notes && (
            <>
              <hr className="divider" />
              <div className="prewrap">{p.notes}</div>
            </>
          )}
        </div>
        <div className="card" style={{ marginTop: 0 }}>
          <h2>Base resume</h2>
          <FileBox
            doc={detail.base_resume}
            path={`/api/candidates/${detail.id}/resume`}
            canUpload
            canDelete={false}
            emptyText="The candidate hasn't uploaded a resume yet."
            onChange={(doc) => setDetail({ ...detail, base_resume: doc })}
          />
        </div>
      </div>

      <h2>Jobs</h2>
      <JobList candidateId={detail.id} />
    </div>
  );
}

function Pref({ label, values }: { label: string; values: string[] }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>
        {values.length ? (
          <div className="chips" style={{ marginTop: 4 }}>
            {values.map((v) => (
              <span className="chip" key={v}>
                {v}
              </span>
            ))}
          </div>
        ) : (
          "—"
        )}
      </dd>
    </div>
  );
}

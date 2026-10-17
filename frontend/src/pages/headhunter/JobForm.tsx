import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import {
  EMPLOYMENT_LABELS,
  EMPLOYMENT_TYPES,
  STATUSES,
  STATUS_LABELS,
  WORK_MODES,
  WORK_MODE_LABELS,
} from "../../lib/format";
import type { CandidateSummary, Job, JobInput, JobOptions } from "../../types";

function today(): string {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

const EMPTY: JobInput = {
  candidate_id: "",
  title: "",
  company: "",
  apply_url: "",
  status: "new",
  category: "",
  employment_type: null,
  location: "",
  work_mode: null,
  compensation: "",
  date_found: today(),
  schedule: "",
  fit_score: null,
  notes: "",
};

// Create or edit a job posting (headhunters).
export default function JobForm() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const editing = Boolean(id);

  const [form, setForm] = useState<JobInput>({
    ...EMPTY,
    candidate_id: params.get("candidate") ?? "",
  });
  const [candidates, setCandidates] = useState<CandidateSummary[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<CandidateSummary[]>("/api/candidates").then(setCandidates).catch(() => {});
    api
      .get<JobOptions>("/api/jobs/options")
      .then((o) => setCategories(o.categories))
      .catch(() => {});
    if (id) {
      api
        .get<Job>(`/api/jobs/${id}`)
        .then((j) => {
          const { candidate_name: _n, optimized_resume: _r, created_at: _c, updated_at: _u, id: _i, ...input } = j;
          setForm(input);
        })
        .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load job"));
    }
  }, [id]);

  const set = <K extends keyof JobInput>(key: K, value: JobInput[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      let job: Job;
      if (editing) {
        const { candidate_id: _c, ...changes } = form;
        job = await api.patch<Job>(`/api/jobs/${id}`, changes);
      } else {
        job = await api.post<Job>("/api/jobs", form);
      }
      navigate(`/jobs/${job.id}`, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page narrow">
      <h1>{editing ? "Edit job" : "Add a job"}</h1>
      <p className="subtitle">
        {editing
          ? "Update the posting. Candidates see changes immediately."
          : "Post an opening for a candidate. You can attach a tailored resume next."}
      </p>
      {error && <div className="alert error">{error}</div>}

      <form className="card" onSubmit={submit}>
        <div className="field">
          <label htmlFor="candidate">
            Candidate <span className="req">*</span>
          </label>
          <select
            id="candidate"
            value={form.candidate_id}
            onChange={(e) => set("candidate_id", e.target.value)}
            required
            disabled={editing}
          >
            <option value="">Choose a candidate…</option>
            {candidates.map((c) => (
              <option key={c.id} value={c.id}>
                {c.display_name} ({c.email})
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label htmlFor="title">
            Role name / job title <span className="req">*</span>
          </label>
          <input
            id="title"
            type="text"
            value={form.title}
            maxLength={255}
            onChange={(e) => set("title", e.target.value)}
            required
          />
        </div>

        <div className="field">
          <label htmlFor="company">Company</label>
          <input
            id="company"
            type="text"
            value={form.company}
            maxLength={255}
            onChange={(e) => set("company", e.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="apply_url">
            Apply link <span className="req">*</span>
          </label>
          <input
            id="apply_url"
            type="url"
            inputMode="url"
            placeholder="https://"
            value={form.apply_url}
            onChange={(e) => set("apply_url", e.target.value)}
            required
          />
        </div>

        <div className="grid two">
          <div className="field">
            <label htmlFor="status">Status</label>
            <select
              id="status"
              value={form.status}
              onChange={(e) => set("status", e.target.value as JobInput["status"])}
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABELS[s]}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="category">Job category</label>
            <input
              id="category"
              type="text"
              list="category-options"
              value={form.category}
              maxLength={120}
              placeholder="e.g. Engineering"
              onChange={(e) => set("category", e.target.value)}
            />
            <datalist id="category-options">
              {categories.map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
          </div>
          <div className="field">
            <label htmlFor="employment_type">Employment type</label>
            <select
              id="employment_type"
              value={form.employment_type ?? ""}
              onChange={(e) =>
                set("employment_type", (e.target.value || null) as JobInput["employment_type"])
              }
            >
              <option value="">—</option>
              {EMPLOYMENT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {EMPLOYMENT_LABELS[t]}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="work_mode">Work arrangement</label>
            <select
              id="work_mode"
              value={form.work_mode ?? ""}
              onChange={(e) => set("work_mode", (e.target.value || null) as JobInput["work_mode"])}
            >
              <option value="">—</option>
              {WORK_MODES.map((m) => (
                <option key={m} value={m}>
                  {WORK_MODE_LABELS[m]}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="location">Location</label>
            <input
              id="location"
              type="text"
              value={form.location}
              maxLength={255}
              onChange={(e) => set("location", e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="compensation">Compensation</label>
            <input
              id="compensation"
              type="text"
              value={form.compensation}
              maxLength={255}
              placeholder="e.g. $150k–$180k + bonus"
              onChange={(e) => set("compensation", e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="schedule">Shift / schedule</label>
            <input
              id="schedule"
              type="text"
              value={form.schedule}
              maxLength={255}
              placeholder="e.g. Mon–Fri, 9–5"
              onChange={(e) => set("schedule", e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="date_found">Date found</label>
            <input
              id="date_found"
              type="date"
              value={form.date_found}
              onChange={(e) => set("date_found", e.target.value)}
              required
            />
          </div>
        </div>

        <div className="field">
          <label>Job fit</label>
          <div className="fit-picker" role="radiogroup" aria-label="Job fit, 1 to 5">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                role="radio"
                aria-checked={form.fit_score === n}
                className={form.fit_score != null && n <= form.fit_score ? "on" : ""}
                onClick={() => set("fit_score", form.fit_score === n ? null : n)}
              >
                {n}
              </button>
            ))}
          </div>
          <div className="help">1 = weak match, 5 = excellent. Tap again to clear.</div>
        </div>

        <div className="field">
          <label htmlFor="notes">Notes</label>
          <textarea
            id="notes"
            value={form.notes}
            onChange={(e) => set("notes", e.target.value)}
            placeholder="Why it fits, recruiter contact, anything the candidate should know…"
          />
        </div>

        <div className="sticky-actions">
          <button className="btn" disabled={busy}>
            {busy ? "Saving…" : editing ? "Save changes" : "Post job"}
          </button>
          <button type="button" className="btn secondary" onClick={() => navigate(-1)}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

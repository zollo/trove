import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import ChipInput from "../components/ChipInput";
import FileBox from "../components/FileBox";
import GoogleAccount from "../components/GoogleAccount";
import ToggleGroup from "../components/ToggleGroup";
import {
  EMPLOYMENT_LABELS,
  EMPLOYMENT_TYPES,
  WORK_MODES,
  WORK_MODE_LABELS,
} from "../lib/format";
import type { CandidateDetail, DocumentMeta, JobOptions, Profile as ProfileT } from "../types";

// Candidate: base resume + what they're looking for.
export default function Profile() {
  const [detail, setDetail] = useState<CandidateDetail | null>(null);
  const [profile, setProfile] = useState<ProfileT | null>(null);
  const [categories, setCategories] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .get<CandidateDetail>("/api/candidates/me")
      .then((d) => {
        setDetail(d);
        setProfile(d.profile);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load profile"));
    api
      .get<JobOptions>("/api/jobs/options")
      .then((o) => setCategories(o.categories))
      .catch(() => {});
  }, []);

  if (error && !profile) {
    return (
      <div className="page narrow">
        <div className="alert error">{error}</div>
      </div>
    );
  }
  if (!profile || !detail) return <div className="page narrow muted">Loading…</div>;

  const set = <K extends keyof ProfileT>(key: K, value: ProfileT[K]) => {
    setSaved(false);
    setProfile({ ...profile, [key]: value });
  };

  const num = (v: string) => (v === "" ? null : Math.max(0, Math.round(Number(v))));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const updated = await api.put<ProfileT>("/api/candidates/me/profile", profile);
      setProfile(updated);
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page narrow">
      <h1>Your profile</h1>
      <p className="subtitle">
        Your headhunter uses this to find and tailor jobs for you.
      </p>

      <div className="card">
        <h2>Base resume</h2>
        <p className="muted small" style={{ marginTop: -6 }}>
          Upload one detailed, generic resume. It gets rewritten for each job you're matched
          with. PDF, Word, or text files up to 10&nbsp;MB.
        </p>
        <FileBox
          doc={detail.base_resume}
          path="/api/candidates/me/resume"
          canUpload
          emptyText="No resume uploaded yet."
          onChange={(doc: DocumentMeta | null) => setDetail({ ...detail, base_resume: doc })}
        />
      </div>

      <form className="card" onSubmit={submit}>
        <h2>What you're looking for</h2>
        {error && <div className="alert error">{error}</div>}

        <div className="field">
          <label htmlFor="headline">Headline</label>
          <input
            id="headline"
            type="text"
            value={profile.headline}
            maxLength={255}
            placeholder="e.g. Senior platform engineer, 10 yrs Kubernetes"
            onChange={(e) => set("headline", e.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="titles">Job titles</label>
          <ChipInput
            id="titles"
            values={profile.desired_titles}
            onChange={(v) => set("desired_titles", v)}
            placeholder="e.g. Site Reliability Engineer"
          />
        </div>

        <div className="field">
          <label htmlFor="categories">Job categories</label>
          <ChipInput
            id="categories"
            values={profile.job_categories}
            onChange={(v) => set("job_categories", v)}
            placeholder="e.g. Engineering"
            suggestions={categories}
          />
        </div>

        <div className="field">
          <label>Employment types</label>
          <ToggleGroup
            options={EMPLOYMENT_TYPES}
            labels={EMPLOYMENT_LABELS}
            values={profile.employment_types}
            onChange={(v) => set("employment_types", v)}
          />
        </div>

        <div className="field">
          <label htmlFor="locations">Locations</label>
          <ChipInput
            id="locations"
            values={profile.locations}
            onChange={(v) => set("locations", v)}
            placeholder="e.g. Denver, CO"
            commaSeparates={false}
          />
        </div>

        <div className="field">
          <label>Work arrangement</label>
          <ToggleGroup
            options={WORK_MODES}
            labels={WORK_MODE_LABELS}
            values={profile.work_modes}
            onChange={(v) => set("work_modes", v)}
          />
        </div>

        <div className="field">
          <label className="check">
            <input
              type="checkbox"
              checked={profile.willing_to_relocate}
              onChange={(e) => set("willing_to_relocate", e.target.checked)}
            />
            Willing to relocate
          </label>
        </div>

        <div className="field">
          <label>Salary range</label>
          <div className="grid two">
            <input
              type="number"
              inputMode="numeric"
              min={0}
              placeholder="Minimum"
              aria-label="Minimum salary"
              value={profile.salary_min ?? ""}
              onChange={(e) => set("salary_min", num(e.target.value))}
            />
            <input
              type="number"
              inputMode="numeric"
              min={0}
              placeholder="Maximum"
              aria-label="Maximum salary"
              value={profile.salary_max ?? ""}
              onChange={(e) => set("salary_max", num(e.target.value))}
            />
            <input
              type="text"
              maxLength={3}
              aria-label="Currency"
              placeholder="Currency"
              value={profile.salary_currency}
              onChange={(e) => set("salary_currency", e.target.value.toUpperCase())}
            />
            <select
              aria-label="Salary period"
              value={profile.salary_period}
              onChange={(e) => set("salary_period", e.target.value as ProfileT["salary_period"])}
            >
              <option value="year">per year</option>
              <option value="hour">per hour</option>
            </select>
          </div>
        </div>

        <div className="field">
          <label htmlFor="notes">Anything else?</label>
          <textarea
            id="notes"
            value={profile.notes}
            maxLength={10000}
            placeholder="Must-haves, deal-breakers, industries to avoid, start date…"
            onChange={(e) => set("notes", e.target.value)}
          />
        </div>

        <div className="sticky-actions">
          <button className="btn" disabled={busy}>
            {busy ? "Saving…" : "Save preferences"}
          </button>
          {saved && <span className="alert success" style={{ margin: 0 }}>Saved</span>}
        </div>
      </form>

      <GoogleAccount returnTo="/profile" />
    </div>
  );
}

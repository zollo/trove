import type { EmploymentType, JobStatus, Profile, WorkMode } from "../types";

export const STATUS_LABELS: Record<JobStatus, string> = {
  new: "New",
  interested: "Interested",
  applied: "Applied",
  interviewing: "Interviewing",
  offer: "Offer",
  rejected: "Rejected",
  not_interested: "Not interested",
  expired: "Expired",
  unavailable: "No longer available",
};

export const STATUSES = Object.keys(STATUS_LABELS) as JobStatus[];

export const EMPLOYMENT_LABELS: Record<EmploymentType, string> = {
  permanent: "Permanent",
  contract: "Contract",
  contract_to_hire: "Contract to hire",
  part_time: "Part-time",
  temporary: "Temporary",
  internship: "Internship",
  freelance: "Freelance",
  other: "Other",
};

export const EMPLOYMENT_TYPES = Object.keys(EMPLOYMENT_LABELS) as EmploymentType[];

export const WORK_MODE_LABELS: Record<WorkMode, string> = {
  onsite: "On-site",
  hybrid: "Hybrid",
  remote: "Remote",
};

export const WORK_MODES = Object.keys(WORK_MODE_LABELS) as WorkMode[];

// Filter groups on the jobs list.
export const STATUS_GROUPS: { key: string; label: string; statuses: JobStatus[] | null }[] = [
  { key: "open", label: "Open", statuses: ["new", "interested", "applied", "interviewing", "offer"] },
  { key: "new", label: "New", statuses: ["new"] },
  { key: "applied", label: "Applied", statuses: ["applied", "interviewing", "offer"] },
  {
    key: "closed",
    label: "Closed",
    statuses: ["rejected", "not_interested", "expired", "unavailable"],
  },
  { key: "all", label: "All", statuses: null },
];

export function formatDate(iso: string): string {
  // Dates (YYYY-MM-DD) are calendar days: parse them as local, not UTC.
  const d = /^\d{4}-\d{2}-\d{2}$/.test(iso) ? new Date(`${iso}T00:00:00`) : new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function formatSalary(p: Pick<Profile, "salary_min" | "salary_max" | "salary_currency" | "salary_period">): string {
  const fmt = (n: number) => {
    try {
      return new Intl.NumberFormat(undefined, {
        style: "currency",
        currency: p.salary_currency || "USD",
        maximumFractionDigits: 0,
      }).format(n);
    } catch {
      // Unknown currency code: show the number with the code instead of crashing.
      return `${n.toLocaleString()} ${p.salary_currency}`;
    }
  };
  const per = p.salary_period === "hour" ? "/hr" : "/yr";
  if (p.salary_min != null && p.salary_max != null) return `${fmt(p.salary_min)}–${fmt(p.salary_max)}${per}`;
  if (p.salary_min != null) return `${fmt(p.salary_min)}+${per}`;
  if (p.salary_max != null) return `up to ${fmt(p.salary_max)}${per}`;
  return "";
}

/** `resume.md` -> `resume.pdf` */
export function exportName(filename: string, format: string): string {
  const dot = filename.lastIndexOf(".");
  return `${dot > 0 ? filename.slice(0, dot) : filename || "resume"}.${format}`;
}

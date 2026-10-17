export type Role = "candidate" | "headhunter";

export type JobStatus =
  | "new"
  | "interested"
  | "applied"
  | "interviewing"
  | "offer"
  | "rejected"
  | "not_interested"
  | "expired"
  | "unavailable";

export type EmploymentType =
  | "permanent"
  | "contract"
  | "contract_to_hire"
  | "part_time"
  | "temporary"
  | "internship"
  | "freelance"
  | "other";

export type WorkMode = "onsite" | "hybrid" | "remote";

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  user: User;
}

export interface AuthConfig {
  registration_enabled: boolean;
}

export interface DocumentMeta {
  id: string;
  kind: "base_resume" | "optimized_resume";
  candidate_id: string;
  job_id: string | null;
  filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
  updated_at: string;
}

export interface Profile {
  headline: string;
  desired_titles: string[];
  job_categories: string[];
  employment_types: EmploymentType[];
  locations: string[];
  work_modes: WorkMode[];
  willing_to_relocate: boolean;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string;
  salary_period: "year" | "hour";
  notes: string;
  updated_at?: string | null;
}

export interface CandidateSummary {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  headline: string;
  has_base_resume: boolean;
  job_count: number;
  open_job_count: number;
}

export interface CandidateDetail {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  profile: Profile;
  base_resume: DocumentMeta | null;
}

export interface Job {
  id: string;
  candidate_id: string;
  candidate_name: string;
  title: string;
  company: string;
  apply_url: string;
  status: JobStatus;
  category: string;
  employment_type: EmploymentType | null;
  location: string;
  work_mode: WorkMode | null;
  compensation: string;
  date_found: string;
  schedule: string;
  fit_score: number | null;
  notes: string;
  optimized_resume: DocumentMeta | null;
  created_at: string;
  updated_at: string;
}

export type JobInput = Omit<
  Job,
  "id" | "candidate_name" | "optimized_resume" | "created_at" | "updated_at"
>;

export interface Option {
  value: string;
  label: string;
}

export interface JobOptions {
  statuses: Option[];
  employment_types: Option[];
  work_modes: Option[];
  salary_periods: Option[];
  categories: string[];
}

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  last_used_at: string | null;
  key?: string;
}

export interface BuildInfo {
  version: string;
  git_commit: string;
  build_time: string;
  environment: string;
  public_url: string;
  api_docs_url: string;
  openapi_url: string;
  mcp_url: string;
}

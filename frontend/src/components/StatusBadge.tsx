import { STATUS_LABELS } from "../lib/format";
import type { JobStatus } from "../types";

export default function StatusBadge({ status }: { status: JobStatus }) {
  return <span className={`badge st-${status}`}>{STATUS_LABELS[status] ?? status}</span>;
}

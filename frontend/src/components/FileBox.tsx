import { useRef, useState, type ChangeEvent } from "react";
import { api, ApiError } from "../api/client";
import { exportName, formatBytes, formatDate } from "../lib/format";
import type { DocumentMeta } from "../types";

const ACCEPT = ".pdf,.docx,.doc,.odt,.rtf,.txt,.md,.html";

// Formats the API can convert a resume to (`?format=`), with button labels.
const EXPORTS = [
  { format: "pdf", label: "PDF" },
  { format: "docx", label: "Word" },
] as const;

// Shows an uploaded resume with download / replace / remove actions.
export default function FileBox({
  doc,
  path,
  canUpload,
  canDelete = canUpload,
  convertible = false,
  emptyText,
  onChange,
}: {
  doc: DocumentMeta | null;
  /** API path of the file, e.g. /api/candidates/me/resume */
  path: string;
  canUpload: boolean;
  canDelete?: boolean;
  /** Offer PDF / Word downloads converted by the server. */
  convertible?: boolean;
  emptyText: string;
  onChange?: (doc: DocumentMeta | null) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (fn: () => Promise<void>) => {
    setError(null);
    setBusy(true);
    try {
      await fn();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  const onFile = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    void run(async () => {
      const saved = await api.upload<DocumentMeta>(path, file);
      onChange?.(saved);
    });
  };

  const remove = () => {
    if (!confirm("Remove this resume?")) return;
    void run(async () => {
      await api.del(path);
      onChange?.(null);
    });
  };

  return (
    <div className="stack" style={{ gap: 8 }}>
      {error && <div className="alert error">{error}</div>}
      {doc ? (
        <div className="file-row">
          <div style={{ minWidth: 0 }}>
            <div className="name">📄 {doc.filename}</div>
            <div className="muted small">
              {formatBytes(doc.size_bytes)} · updated {formatDate(doc.updated_at)}
            </div>
          </div>
          <div className="row">
            <button
              type="button"
              className="btn small"
              disabled={busy}
              onClick={() => void run(() => api.download(path, doc.filename))}
            >
              {convertible ? "Original" : "Download"}
            </button>
            {convertible &&
              EXPORTS.map(({ format, label }) => (
                <button
                  key={format}
                  type="button"
                  className="btn small"
                  disabled={busy}
                  title={`Download as ${label}`}
                  onClick={() =>
                    void run(() =>
                      api.download(`${path}?format=${format}`, exportName(doc.filename, format)),
                    )
                  }
                >
                  {label}
                </button>
              ))}
            {canUpload && (
              <button
                type="button"
                className="btn secondary small"
                disabled={busy}
                onClick={() => input.current?.click()}
              >
                Replace
              </button>
            )}
            {canDelete && (
              <button type="button" className="btn danger small" disabled={busy} onClick={remove}>
                Remove
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="file-row">
          <span className="muted">{emptyText}</span>
          {canUpload && (
            <button
              type="button"
              className="btn small"
              disabled={busy}
              onClick={() => input.current?.click()}
            >
              {busy ? "Uploading…" : "Upload"}
            </button>
          )}
        </div>
      )}
      {canUpload && (
        <input ref={input} type="file" accept={ACCEPT} hidden onChange={onFile} />
      )}
    </div>
  );
}

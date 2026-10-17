import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { BuildInfo } from "../types";

export default function Info() {
  const [info, setInfo] = useState<BuildInfo | null>(null);

  useEffect(() => {
    api.get<BuildInfo>("/api/build-info").then(setInfo).catch(() => {});
  }, []);

  const frontend = {
    version: import.meta.env.VITE_APP_VERSION ?? "dev",
    commit: import.meta.env.VITE_GIT_COMMIT ?? "unknown",
  };

  return (
    <div className="page narrow">
      <h1>About Trove</h1>
      <p className="subtitle">
        A shared space for you and your headhunter: they post openings that fit, you track
        where you've applied.
      </p>
      <div className="card">
        <dl className="facts">
          <div>
            <dt>Server version</dt>
            <dd>{info?.version ?? "…"}</dd>
          </div>
          <div>
            <dt>App version</dt>
            <dd>{frontend.version}</dd>
          </div>
          <div>
            <dt>Commit</dt>
            <dd>
              <code>{(info?.git_commit ?? frontend.commit).slice(0, 12)}</code>
            </dd>
          </div>
          <div>
            <dt>Built</dt>
            <dd>{info?.build_time ?? "…"}</dd>
          </div>
        </dl>
      </div>
      <p className="muted small" style={{ marginTop: 16 }}>
        <a href="https://github.com/zollo/trove" target="_blank" rel="noopener noreferrer">
          github.com/zollo/trove
        </a>
      </p>
    </div>
  );
}

import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { AuthConfig, User } from "../types";
import GoogleButton from "./GoogleButton";

// Link or unlink a Google account for the signed-in user. Hidden when Google
// sign-in isn't configured on the server.
export default function GoogleAccount({ returnTo }: { returnTo: string }) {
  const { user, setUser } = useAuth();
  const [enabled, setEnabled] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .get<AuthConfig>("/api/auth/config")
      .then((c) => setEnabled(c.google_enabled))
      .catch(() => {});
  }, []);

  if (!user || (!enabled && !user.google_email)) return null;

  const unlink = async () => {
    if (!confirm("Unlink Google? You'll sign in with your email and password.")) return;
    setError(null);
    setBusy(true);
    try {
      setUser(await api.del<User>("/api/auth/google/link"));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to unlink Google");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card">
      <h2>Google sign-in</h2>
      {error && <div className="alert error">{error}</div>}
      {user.google_email ? (
        <div className="file-row">
          <div>
            <div className="name">Linked to {user.google_email}</div>
            <div className="muted small">
              {user.has_password
                ? "You can sign in with Google or with your password."
                : "You sign in with Google. Ask a headhunter to set a password before unlinking."}
            </div>
          </div>
          {user.has_password && (
            <button className="btn danger small" onClick={() => void unlink()} disabled={busy}>
              Unlink
            </button>
          )}
        </div>
      ) : (
        <>
          <p className="muted small" style={{ marginTop: -6 }}>
            Link your Google account to sign in to Trove with one click.
          </p>
          <GoogleButton
            intent="link"
            label="Link Google account"
            returnTo={returnTo}
            onError={setError}
            className="btn secondary"
          />
        </>
      )}
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { Token } from "../types";

// Magic sign-in link from a headhunter: /auth/link#<token>. The token lives in
// the fragment so it never reaches server logs; it is redeemed with a POST, so
// link previews and mail scanners that merely fetch the page can't use it up.
export default function LoginLinkPage() {
  const navigate = useNavigate();
  const { user, loading, acceptToken } = useAuth();
  const [token] = useState(() => window.location.hash.replace(/^#/, ""));
  const [error, setError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    // Keep the token out of the address bar and history.
    if (window.location.hash) {
      window.history.replaceState(null, "", window.location.pathname);
    }
  }, []);

  // Someone already signed in here must agree to switch accounts first.
  const needsConfirm = !!user && !confirmed;

  useEffect(() => {
    if (loading || needsConfirm) return;
    // StrictMode runs effects twice; the link works only once.
    if (started.current) return;
    started.current = true;
    if (!token) {
      setError("This sign-in link is incomplete. Ask for a new one.");
      return;
    }
    api
      .post<Token>("/api/auth/login-link", { token })
      .then((t) => {
        acceptToken(t);
        navigate("/", { replace: true });
      })
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Signing in with this link failed."),
      );
  }, [loading, needsConfirm, token, acceptToken, navigate]);

  return (
    <div className="center-screen">
      <div className="card" style={{ width: "100%", maxWidth: 400 }}>
        {error ? (
          <>
            <div className="alert error">{error}</div>
            <p className="muted small">Sign-in links work once and expire after 24 hours.</p>
            <Link to="/login" className="btn secondary block">
              Go to sign in
            </Link>
          </>
        ) : needsConfirm ? (
          <>
            <p>
              You're signed in as <strong>{user?.email}</strong>. Use this link to sign in as
              someone else?
            </p>
            <div className="row">
              {/* The current session is replaced only once the link is redeemed. */}
              <button className="btn" onClick={() => setConfirmed(true)}>
                Switch account
              </button>
              <Link to="/" className="btn secondary">
                Stay signed in
              </Link>
            </div>
          </>
        ) : (
          <p className="muted" style={{ textAlign: "center" }}>
            Signing you in…
          </p>
        )}
      </div>
    </div>
  );
}

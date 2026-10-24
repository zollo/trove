import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { takePendingGoogle } from "../lib/google";
import type { Token, User } from "../types";

// Google redirects here (GOOGLE_REDIRECT_URI) with ?code&state, or ?error.
export default function GoogleCallback() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { acceptToken, setUser } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [linkFlow, setLinkFlow] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    // StrictMode runs effects twice; the code can only be redeemed once.
    if (started.current) return;
    started.current = true;

    const pending = takePendingGoogle();
    const code = params.get("code");
    const state = params.get("state");
    setLinkFlow(pending?.intent === "link");

    if (params.get("error")) {
      setError(
        params.get("error") === "access_denied"
          ? "Google sign-in was cancelled."
          : `Google sign-in failed (${params.get("error")}).`,
      );
      return;
    }
    if (!pending || !code || !state || state !== pending.state) {
      setError("This Google sign-in link is invalid or has already been used. Please try again.");
      return;
    }

    const body = { code, state, code_verifier: pending.code_verifier };
    const finish =
      pending.intent === "link"
        ? api.post<User>("/api/auth/google/link", body).then((u) => {
            setUser(u);
            navigate(pending.returnTo, { replace: true });
          })
        : api.post<Token>("/api/auth/google/login", body).then((t) => {
            acceptToken(t);
            navigate("/", { replace: true });
          });
    finish.catch((err) =>
      setError(err instanceof ApiError ? err.message : "Google sign-in failed."),
    );
  }, [params, navigate, acceptToken, setUser]);

  return (
    <div className="center-screen">
      <div className="card" style={{ width: "100%", maxWidth: 400 }}>
        {error ? (
          <>
            <div className="alert error">{error}</div>
            <Link to={linkFlow ? "/" : "/login"} className="btn secondary block">
              {linkFlow ? "Back to Trove" : "Back to sign in"}
            </Link>
          </>
        ) : (
          <p className="muted" style={{ textAlign: "center" }}>
            Signing in with Google…
          </p>
        )}
      </div>
    </div>
  );
}

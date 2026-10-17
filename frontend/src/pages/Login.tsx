import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { AuthConfig } from "../types";

export default function Login() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [config, setConfig] = useState<AuthConfig>({ registration_enabled: true });

  useEffect(() => {
    if (user) navigate("/");
  }, [user, navigate]);

  useEffect(() => {
    api.get<AuthConfig>("/api/auth/config").then(setConfig).catch(() => {});
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="center-screen">
      <div className="card" style={{ width: "100%", maxWidth: 400 }}>
        <div className="brand" style={{ marginBottom: 8 }}>
          <img src="/favicon.svg" alt="" />
          Trove
        </div>
        <p className="subtitle">Your job search, organised with your headhunter.</p>

        {error && <div className="alert error">{error}</div>}

        <form onSubmit={submit}>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button className="btn block" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        {config.registration_enabled && (
          <p className="muted" style={{ marginTop: 18, textAlign: "center" }}>
            Looking for work? <Link to="/register">Create a candidate account</Link>
          </p>
        )}
      </div>
    </div>
  );
}

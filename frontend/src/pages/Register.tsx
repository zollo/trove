import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import GoogleButton from "../components/GoogleButton";
import { useAuth } from "../context/AuthContext";
import type { AuthConfig } from "../types";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [googleEnabled, setGoogleEnabled] = useState(false);

  useEffect(() => {
    api
      .get<AuthConfig>("/api/auth/config")
      .then((c) => setGoogleEnabled(c.google_enabled))
      .catch(() => {});
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await register(email, password, name);
      // New candidates start by telling us what they're looking for.
      navigate("/profile");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Registration failed");
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
        <p className="subtitle">Create your candidate account.</p>
        {error && <div className="alert error">{error}</div>}
        <form onSubmit={submit}>
          <div className="field">
            <label htmlFor="name">Your name</label>
            <input
              id="name"
              type="text"
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <div className="help">At least 8 characters.</div>
          </div>
          <button className="btn block" disabled={busy}>
            {busy ? "Creating account…" : "Create account"}
          </button>
        </form>
        {googleEnabled && (
          <>
            <hr className="divider" />
            <GoogleButton intent="login" label="Sign up with Google" onError={setError} />
          </>
        )}
        <p className="muted" style={{ marginTop: 18, textAlign: "center" }}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}

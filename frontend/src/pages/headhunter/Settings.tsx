import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../../api/client";
import GoogleAccount from "../../components/GoogleAccount";
import { useAuth } from "../../context/AuthContext";
import { formatDate } from "../../lib/format";
import type { ApiKey, BuildInfo, Role, User } from "../../types";

export default function Settings() {
  return (
    <div className="page narrow">
      <h1>Settings</h1>
      <p className="subtitle">Connect AI headhunters and manage accounts.</p>
      <Connect />
      <ApiKeys />
      <GoogleAccount returnTo="/settings" />
      <Users />
    </div>
  );
}

function Connect() {
  const [info, setInfo] = useState<BuildInfo | null>(null);
  useEffect(() => {
    api.get<BuildInfo>("/api/build-info").then(setInfo).catch(() => {});
  }, []);
  const origin = window.location.origin;
  const mcpUrl = `${origin}/mcp`;
  const config = JSON.stringify(
    {
      mcpServers: {
        trove: {
          type: "http",
          url: mcpUrl,
          headers: { Authorization: "Bearer <your API key>" },
        },
      },
    },
    null,
    2,
  );

  return (
    <div className="card">
      <h2>Connect an AI headhunter</h2>
      <p className="muted small" style={{ marginTop: -6 }}>
        Point Claude, ChatGPT or any MCP client at Trove's MCP endpoint with an API key from
        below. The same operations are available as a REST API.
      </p>
      <dl className="facts">
        <div>
          <dt>MCP endpoint</dt>
          <dd>
            <code>{mcpUrl}</code>
          </dd>
        </div>
        <div>
          <dt>REST API</dt>
          <dd>
            <a href="/docs" target="_blank" rel="noreferrer">
              Swagger UI
            </a>{" "}
            ·{" "}
            <a href="/openapi.json" target="_blank" rel="noreferrer">
              OpenAPI spec
            </a>
          </dd>
        </div>
        <div>
          <dt>Version</dt>
          <dd>{info?.version ?? "…"}</dd>
        </div>
      </dl>
      <details style={{ marginTop: 12 }}>
        <summary>Example MCP client config</summary>
        <pre>{config}</pre>
        <p className="muted small">
          Claude Code: <code>claude mcp add --transport http trove {mcpUrl} --header
          "Authorization: Bearer &lt;key&gt;"</code>
        </p>
      </details>
    </div>
  );
}

function ApiKeys() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [name, setName] = useState("");
  const [created, setCreated] = useState<ApiKey | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => api.get<ApiKey[]>("/api/api-keys").then(setKeys).catch(() => {});
  useEffect(() => {
    void load();
  }, []);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const key = await api.post<ApiKey>("/api/api-keys", { name });
      setCreated(key);
      setName("");
      void load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create key");
    }
  };

  const revoke = async (key: ApiKey) => {
    if (!confirm(`Revoke "${key.name}"? Tools using it will stop working.`)) return;
    await api.del(`/api/api-keys/${key.id}`);
    void load();
  };

  return (
    <div className="card">
      <h2>API keys</h2>
      {error && <div className="alert error">{error}</div>}
      {created?.key && (
        <div className="alert success">
          <strong>Copy this key now; it won't be shown again.</strong>
          <div className="secret" style={{ marginTop: 8 }}>
            {created.key}
          </div>
          <button
            type="button"
            className="btn small"
            style={{ marginTop: 8 }}
            onClick={() => void navigator.clipboard?.writeText(created.key ?? "")}
          >
            Copy
          </button>
        </div>
      )}
      <form className="row" onSubmit={create} style={{ flexWrap: "nowrap", marginBottom: 12 }}>
        <input
          type="text"
          placeholder="Key name, e.g. Claude"
          aria-label="Key name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <button className="btn">Create</button>
      </form>
      {keys.length === 0 ? (
        <p className="muted small">No API keys yet.</p>
      ) : (
        <div className="list">
          {keys.map((k) => (
            <div key={k.id} className="file-row">
              <div>
                <div className="name">{k.name}</div>
                <div className="muted small">
                  <code>{k.prefix}…</code> · created {formatDate(k.created_at)} ·{" "}
                  {k.last_used_at ? `last used ${formatDate(k.last_used_at)}` : "never used"}
                </div>
              </div>
              <button className="btn danger small" onClick={() => void revoke(k)}>
                Revoke
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Users() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [form, setForm] = useState({
    email: "",
    display_name: "",
    password: "",
    role: "candidate" as Role,
  });
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  const load = () => api.get<User[]>("/api/users").then(setUsers).catch(() => {});
  useEffect(() => {
    void load();
  }, []);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setOk(null);
    try {
      const u = await api.post<User>("/api/users", form);
      setOk(`Created ${u.email}. Share the password with them securely.`);
      setForm({ email: "", display_name: "", password: "", role: form.role });
      void load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create user");
    }
  };

  const toggle = async (u: User) => {
    try {
      await api.patch(`/api/users/${u.id}`, { is_active: !u.is_active });
      void load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Update failed");
    }
  };

  return (
    <div className="card" id="users">
      <h2>People</h2>
      {error && <div className="alert error">{error}</div>}
      {ok && <div className="alert success">{ok}</div>}
      <div className="list" style={{ marginBottom: 16 }}>
        {users.map((u) => (
          <div key={u.id} className="file-row">
            <div style={{ minWidth: 0 }}>
              <div className="name">
                {u.display_name}{" "}
                <span className={`badge ${u.role === "headhunter" ? "st-offer" : "st-new"}`}>
                  {u.role}
                </span>
                {!u.is_active && <span className="badge st-expired"> inactive</span>}
              </div>
              <div className="muted small">{u.email}</div>
            </div>
            {u.id !== me?.id && (
              <button className="btn secondary small" onClick={() => void toggle(u)}>
                {u.is_active ? "Deactivate" : "Reactivate"}
              </button>
            )}
          </div>
        ))}
      </div>

      <h3>Add a person</h3>
      <form onSubmit={create}>
        <div className="grid two">
          <div className="field">
            <label htmlFor="u-name">Name</label>
            <input
              id="u-name"
              type="text"
              value={form.display_name}
              onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="u-email">Email</label>
            <input
              id="u-email"
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="u-password">Temporary password</label>
            <input
              id="u-password"
              type="text"
              minLength={8}
              autoComplete="off"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="u-role">Role</label>
            <select
              id="u-role"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value as Role })}
            >
              <option value="candidate">Candidate</option>
              <option value="headhunter">Headhunter</option>
            </select>
          </div>
        </div>
        <button className="btn">Add person</button>
      </form>
    </div>
  );
}

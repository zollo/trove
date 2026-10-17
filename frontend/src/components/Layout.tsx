import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import ThemeToggle from "./ThemeToggle";

interface Tab {
  to: string;
  label: string;
  icon: string;
  end?: boolean;
}

const CANDIDATE_TABS: Tab[] = [
  { to: "/", label: "Jobs", icon: "💼", end: true },
  { to: "/profile", label: "Profile", icon: "👤" },
  { to: "/info", label: "About", icon: "ℹ️" },
];

const HEADHUNTER_TABS: Tab[] = [
  { to: "/", label: "Candidates", icon: "👥", end: true },
  { to: "/jobs", label: "Jobs", icon: "💼", end: true },
  { to: "/jobs/new", label: "Add job", icon: "➕" },
  { to: "/settings", label: "Settings", icon: "⚙️" },
];

export default function Layout() {
  const { user, isHeadhunter, logout } = useAuth();
  const navigate = useNavigate();
  const tabs = isHeadhunter ? HEADHUNTER_TABS : CANDIDATE_TABS;

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <>
      <nav className="app-nav">
        <NavLink to="/" className="brand">
          <img src="/favicon.svg" alt="" />
          Trove
        </NavLink>
        <div className="links">
          {tabs.map((t) => (
            <NavLink key={t.to} to={t.to} end={t.end}>
              {t.label}
            </NavLink>
          ))}
        </div>
        <div className="spacer" />
        <span className="user">{user?.display_name || user?.email}</span>
        <ThemeToggle />
        <button className="btn secondary small" onClick={handleLogout}>
          Sign out
        </button>
      </nav>
      <Outlet />
      <nav className="tabbar" aria-label="Main">
        {tabs.map((t) => (
          <NavLink key={t.to} to={t.to} end={t.end}>
            <span className="ico" aria-hidden>
              {t.icon}
            </span>
            {t.label}
          </NavLink>
        ))}
      </nav>
    </>
  );
}

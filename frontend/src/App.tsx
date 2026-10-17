import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";
import Info from "./pages/Info";
import JobDetail from "./pages/JobDetail";
import Login from "./pages/Login";
import MyJobs from "./pages/MyJobs";
import Profile from "./pages/Profile";
import Register from "./pages/Register";
import AllJobs from "./pages/headhunter/AllJobs";
import CandidateView from "./pages/headhunter/CandidateView";
import Candidates from "./pages/headhunter/Candidates";
import JobForm from "./pages/headhunter/JobForm";
import Settings from "./pages/headhunter/Settings";

function Home() {
  const { isHeadhunter } = useAuth();
  return isHeadhunter ? <Candidates /> : <MyJobs />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Home />} />
        <Route path="/jobs/:id" element={<JobDetail />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/info" element={<Info />} />
      </Route>

      <Route
        element={
          <ProtectedRoute headhunterOnly>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/jobs" element={<AllJobs />} />
        <Route path="/jobs/new" element={<JobForm />} />
        <Route path="/jobs/:id/edit" element={<JobForm />} />
        <Route path="/candidates/:id" element={<CandidateView />} />
        <Route path="/settings" element={<Settings />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

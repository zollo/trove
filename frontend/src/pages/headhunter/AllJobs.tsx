import { Link } from "react-router-dom";
import JobList from "../../components/JobList";

export default function AllJobs() {
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>All jobs</h1>
          <p className="subtitle" style={{ margin: 0 }}>
            Every posting across your candidates.
          </p>
        </div>
        <Link className="btn" to="/jobs/new">
          Add job
        </Link>
      </div>
      <JobList showCandidate />
    </div>
  );
}

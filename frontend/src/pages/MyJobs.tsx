import JobList from "../components/JobList";

// Candidate home: the jobs their headhunter has found for them.
export default function MyJobs() {
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Your jobs</h1>
          <p className="subtitle" style={{ margin: 0 }}>
            Openings your headhunter found for you. Tap one to apply and track it.
          </p>
        </div>
      </div>
      <JobList />
    </div>
  );
}

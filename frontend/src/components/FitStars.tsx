export default function FitStars({ score }: { score: number | null }) {
  if (score == null) return null;
  return (
    <span className="stars" title={`Job fit ${score} of 5`} aria-label={`Job fit ${score} of 5`}>
      {"★".repeat(score)}
      <span className="off">{"★".repeat(5 - score)}</span>
    </span>
  );
}

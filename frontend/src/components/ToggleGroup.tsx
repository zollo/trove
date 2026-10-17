// Multi-select pills for small enum lists (employment types, work modes).
export default function ToggleGroup<T extends string>({
  options,
  labels,
  values,
  onChange,
}: {
  options: T[];
  labels: Record<T, string>;
  values: T[];
  onChange: (values: T[]) => void;
}) {
  return (
    <div className="chips">
      {options.map((o) => {
        const on = values.includes(o);
        return (
          <button
            key={o}
            type="button"
            className={`pill${on ? " active" : ""}`}
            aria-pressed={on}
            onClick={() => onChange(on ? values.filter((v) => v !== o) : [...values, o])}
          >
            {labels[o]}
          </button>
        );
      })}
    </div>
  );
}

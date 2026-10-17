import { useState, type KeyboardEvent } from "react";

// A list-of-strings editor: type a value and press Enter (or comma) to add it.
export default function ChipInput({
  values,
  onChange,
  placeholder,
  suggestions = [],
  id,
}: {
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  suggestions?: string[];
  id?: string;
}) {
  const [draft, setDraft] = useState("");
  const listId = id ? `${id}-suggestions` : undefined;

  const add = (raw: string) => {
    const v = raw.trim().replace(/,$/, "").trim();
    if (v && !values.includes(v)) onChange([...values, v]);
    setDraft("");
  };

  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      add(draft);
    } else if (e.key === "Backspace" && !draft && values.length) {
      onChange(values.slice(0, -1));
    }
  };

  return (
    <div className="stack" style={{ gap: 8 }}>
      {values.length > 0 && (
        <div className="chips">
          {values.map((v) => (
            <span className="chip" key={v}>
              {v}
              <button
                type="button"
                aria-label={`Remove ${v}`}
                onClick={() => onChange(values.filter((x) => x !== v))}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="row" style={{ flexWrap: "nowrap" }}>
        <input
          id={id}
          type="text"
          value={draft}
          placeholder={placeholder}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKey}
          onBlur={() => draft.trim() && add(draft)}
          list={listId}
          enterKeyHint="done"
        />
        <button type="button" className="btn secondary" onClick={() => add(draft)}>
          Add
        </button>
      </div>
      {listId && suggestions.length > 0 && (
        <datalist id={listId}>
          {suggestions.map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
      )}
    </div>
  );
}

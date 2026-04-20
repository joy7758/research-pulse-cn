type ProgressFilterOption = {
  key: string;
  label: string;
  count: number;
};

type ProgressFilterBarProps = {
  options: ProgressFilterOption[];
  activeKey: string;
  onChange: (key: string) => void;
};

export function ProgressFilterBar({
  options,
  activeKey,
  onChange,
}: ProgressFilterBarProps) {
  return (
    <div className="filter-bar" role="toolbar" aria-label="论文进度筛选">
      {options.map((option) => (
        <button
          key={option.key}
          type="button"
          className={`filter-chip ${option.key === activeKey ? "filter-chip-active" : ""}`}
          onClick={() => onChange(option.key)}
          aria-pressed={option.key === activeKey}
        >
          <span>{option.label}</span>
          <strong>{option.count}</strong>
        </button>
      ))}
    </div>
  );
}

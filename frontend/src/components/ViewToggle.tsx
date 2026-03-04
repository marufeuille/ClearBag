type ViewMode = "calendar" | "list";

type Props = {
  mode: ViewMode;
  onChange: (mode: ViewMode) => void;
};

export function ViewToggle({ mode, onChange }: Props) {
  return (
    <div
      role="radiogroup"
      aria-label="表示切り替え"
      className="flex items-center bg-gray-100 rounded-xl p-1 gap-1"
    >
      <button
        role="radio"
        aria-checked={mode === "calendar"}
        onClick={() => onChange("calendar")}
        className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
          mode === "calendar"
            ? "bg-white shadow-sm text-blue-600"
            : "text-gray-400 hover:text-gray-600"
        }`}
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        カレンダー
      </button>
      <button
        role="radio"
        aria-checked={mode === "list"}
        onClick={() => onChange("list")}
        className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
          mode === "list"
            ? "bg-white shadow-sm text-blue-600"
            : "text-gray-400 hover:text-gray-600"
        }`}
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
        </svg>
        リスト
      </button>
    </div>
  );
}

type Props = {
  year: number;
  month: number;
  onPrev: () => void;
  onNext: () => void;
};

export function MonthNavigator({ year, month, onPrev, onNext }: Props) {
  return (
    <div className="flex items-center gap-2">
      <button
        onClick={onPrev}
        aria-label="前の月"
        className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <span className="text-base font-semibold text-gray-700 min-w-[7rem] text-center">
        {year}年{month + 1}月
      </span>
      <button
        onClick={onNext}
        aria-label="次の月"
        className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500 transition-colors"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>
  );
}

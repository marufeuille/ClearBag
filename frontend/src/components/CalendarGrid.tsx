const WEEKDAYS = ["日", "月", "火", "水", "木", "金", "土"] as const;

type Props = {
  year: number;
  month: number;
  eventDates: Set<string>;
  onDateTap: (dateStr: string) => void;
};

function toDateStr(year: number, month: number, day: number): string {
  const mm = String(month + 1).padStart(2, "0");
  const dd = String(day).padStart(2, "0");
  return `${year}-${mm}-${dd}`;
}

export function CalendarGrid({ year, month, eventDates, onDateTap }: Props) {
  const firstDayOfWeek = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const today = new Date();
  const todayStr = toDateStr(today.getFullYear(), today.getMonth(), today.getDate());

  // グリッドセル: 先頭のブランク + 日付
  const cells: (number | null)[] = [
    ...Array(firstDayOfWeek).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];

  return (
    <div>
      {/* 曜日ヘッダー */}
      <div className="grid grid-cols-7 mb-1">
        {WEEKDAYS.map((wd, i) => (
          <div
            key={wd}
            className={`text-center text-xs font-medium py-1 ${
              i === 0 ? "text-red-500" : i === 6 ? "text-blue-500" : "text-gray-400"
            }`}
          >
            {wd}
          </div>
        ))}
      </div>

      {/* 日付グリッド */}
      <div className="grid grid-cols-7">
        {cells.map((day, idx) => {
          if (day === null) {
            return <div key={`blank-${idx}`} />;
          }

          const dateStr = toDateStr(year, month, day);
          const isToday = dateStr === todayStr;
          const hasEvent = eventDates.has(dateStr);
          const colIndex = idx % 7;

          return (
            <button
              key={dateStr}
              onClick={() => onDateTap(dateStr)}
              data-date={dateStr}
              className="flex flex-col items-center py-1.5 gap-0.5 hover:bg-gray-50 rounded-lg transition-colors"
            >
              <span
                className={`text-sm w-8 h-8 flex items-center justify-center rounded-full font-medium ${
                  isToday
                    ? "bg-blue-600 text-white"
                    : colIndex === 0
                    ? "text-red-500"
                    : colIndex === 6
                    ? "text-blue-500"
                    : "text-gray-700"
                }`}
              >
                {day}
              </span>
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  hasEvent ? "bg-blue-400" : "invisible"
                }`}
                aria-hidden="true"
              />
            </button>
          );
        })}
      </div>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { NavBar } from "@/components/NavBar";
import { CalendarGrid } from "@/components/CalendarGrid";
import { EventList } from "@/components/EventList";
import { MonthNavigator } from "@/components/MonthNavigator";
import { ViewToggle } from "@/components/ViewToggle";
import { EventData, getEvents } from "@/lib/api";

type ViewMode = "calendar" | "list";

export default function CalendarPage() {
  const now = new Date();
  const [currentMonth, setCurrentMonth] = useState({
    year: now.getFullYear(),
    month: now.getMonth(),
  });
  const [viewMode, setViewMode] = useState<ViewMode>("calendar");
  const [focusDate, setFocusDate] = useState<string | null>(null);

  const [events, setEvents] = useState<EventData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { from, to } = useMemo(() => {
    const { year, month } = currentMonth;
    const from = new Date(year, month, 1).toISOString().slice(0, 10);
    const to = new Date(year, month + 1, 0).toISOString().slice(0, 10);
    return { from, to };
  }, [currentMonth]);

  useEffect(() => {
    setLoading(true);
    getEvents({ from, to })
      .then(setEvents)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [from, to]);

  const grouped = useMemo(() => {
    const map: Record<string, EventData[]> = {};
    for (const ev of events) {
      const key = ev.start.slice(0, 10);
      (map[key] ??= []).push(ev);
    }
    return Object.entries(map).sort(([a], [b]) => a.localeCompare(b));
  }, [events]);

  const eventDates = useMemo(
    () => new Set(events.map((ev) => ev.start.slice(0, 10))),
    [events]
  );

  const handlePrevMonth = () => {
    setCurrentMonth(({ year, month }) => {
      if (month === 0) return { year: year - 1, month: 11 };
      return { year, month: month - 1 };
    });
  };

  const handleNextMonth = () => {
    setCurrentMonth(({ year, month }) => {
      if (month === 11) return { year: year + 1, month: 0 };
      return { year, month: month + 1 };
    });
  };

  const handleDateTap = (dateStr: string) => {
    setViewMode("list");
    setFocusDate(dateStr);
  };

  const handleClearFocus = useCallback(() => setFocusDate(null), []);

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        <NavBar />
        <main className="max-w-2xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between mb-4">
            <MonthNavigator
              year={currentMonth.year}
              month={currentMonth.month}
              onPrev={handlePrevMonth}
              onNext={handleNextMonth}
            />
            <ViewToggle mode={viewMode} onChange={setViewMode} />
          </div>

          {loading && <p className="text-gray-400 text-sm">読み込み中...</p>}
          {error && <p className="text-red-500 text-sm">{error}</p>}

          {viewMode === "calendar" ? (
            <>
              <CalendarGrid
                year={currentMonth.year}
                month={currentMonth.month}
                eventDates={eventDates}
                onDateTap={handleDateTap}
              />
              {!loading && events.length === 0 && (
                <p className="text-gray-400 text-sm text-center py-4">
                  予定はありません
                </p>
              )}
            </>
          ) : (
            <>
              {!loading && grouped.length === 0 && (
                <p className="text-gray-400 text-sm text-center py-8">
                  予定はありません
                </p>
              )}
              <EventList
                grouped={grouped}
                focusDate={focusDate}
                onClearFocus={handleClearFocus}
              />
            </>
          )}
        </main>
      </div>
    </AuthGuard>
  );
}

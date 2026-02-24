"use client";

import { useEffect, useMemo, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { NavBar } from "@/components/NavBar";
import { EventData, getEvents } from "@/lib/api";

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("ja-JP", {
    month: "short",
    day: "numeric",
    weekday: "short",
  });
}

export default function CalendarPage() {
  const [events, setEvents] = useState<EventData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 今月の範囲を取得
  const { from, to } = useMemo(() => {
    const now = new Date();
    const from = new Date(now.getFullYear(), now.getMonth(), 1)
      .toISOString()
      .slice(0, 10);
    const to = new Date(now.getFullYear(), now.getMonth() + 2, 0)
      .toISOString()
      .slice(0, 10);
    return { from, to };
  }, []);

  useEffect(() => {
    setLoading(true);
    getEvents({ from, to })
      .then(setEvents)
      .catch(() => setError("イベントの取得に失敗しました"))
      .finally(() => setLoading(false));
  }, [from, to]);

  // 日付でグループ化
  const grouped = useMemo(() => {
    const map: Record<string, EventData[]> = {};
    for (const ev of events) {
      const key = ev.start.slice(0, 10);
      (map[key] ??= []).push(ev);
    }
    return Object.entries(map).sort(([a], [b]) => a.localeCompare(b));
  }, [events]);

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        <NavBar />
        <main className="max-w-2xl mx-auto px-4 py-6">
          <h2 className="text-lg font-semibold text-gray-700 mb-4">
            今後の予定
          </h2>

          {loading && <p className="text-gray-400 text-sm">読み込み中...</p>}
          {error && <p className="text-red-500 text-sm">{error}</p>}

          {!loading && grouped.length === 0 && (
            <p className="text-gray-400 text-sm text-center py-8">
              予定はありません
            </p>
          )}

          <div className="flex flex-col gap-4">
            {grouped.map(([date, evs]) => (
              <div key={date}>
                <p className="text-xs font-semibold text-gray-400 uppercase mb-2">
                  {formatDate(date)}
                </p>
                <ul className="flex flex-col gap-2">
                  {evs.map((ev, i) => (
                    <li
                      key={i}
                      className="bg-white rounded-xl shadow-sm p-3 border-l-4 border-blue-400"
                    >
                      <p className="text-sm font-medium text-gray-800">
                        {ev.summary}
                      </p>
                      {ev.location && (
                        <p className="text-xs text-gray-500 mt-0.5">
                          📍 {ev.location}
                        </p>
                      )}
                      {ev.description && (
                        <p className="text-xs text-gray-400 mt-1 line-clamp-2">
                          {ev.description}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}

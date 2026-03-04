"use client";

import { useEffect, useRef } from "react";
import { EventData } from "@/lib/api";

export function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("ja-JP", {
    month: "short",
    day: "numeric",
    weekday: "short",
  });
}

export function formatTimeRange(start: string, end: string): string {
  if (!start.includes("T")) return "終日";
  const fmt = (iso: string) =>
    new Date(iso).toLocaleTimeString("ja-JP", { hour: "numeric", minute: "2-digit" });
  return `${fmt(start)}〜${fmt(end)}`;
}

type Props = {
  grouped: [string, EventData[]][];
  focusDate: string | null;
  onClearFocus: () => void;
};

export function EventList({ grouped, focusDate, onClearFocus }: Props) {
  const groupRefs = useRef<Record<string, HTMLDivElement | null>>({});

  useEffect(() => {
    if (!focusDate) return;
    const el = groupRefs.current[focusDate];
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      const timer = setTimeout(onClearFocus, 500);
      return () => clearTimeout(timer);
    }
  }, [focusDate, onClearFocus]);

  return (
    <div className="flex flex-col gap-4">
      {grouped.map(([date, evs]) => (
        <div
          key={date}
          ref={(el) => { groupRefs.current[date] = el; }}
        >
          <p className="text-xs font-semibold text-gray-400 uppercase mb-2">
            {formatDate(date)}
          </p>
          <ul className="flex flex-col gap-2">
            {evs.map((ev, i) => (
              <li
                key={i}
                className="bg-white rounded-xl shadow-sm p-3 border-l-4 border-blue-400"
              >
                <p className="text-sm font-medium text-gray-800">{ev.summary}</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {formatTimeRange(ev.start, ev.end)}
                </p>
                {ev.location && (
                  <p className="text-xs text-gray-500 mt-0.5">📍 {ev.location}</p>
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
  );
}

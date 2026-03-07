"use client";

import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { NavBar } from "@/components/NavBar";
import { TaskData, getTasks, completeTask } from "@/lib/api";
import { sendEvent } from "@/lib/analytics";

export default function TasksPage() {
  const [tasks, setTasks] = useState<TaskData[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCompleted, setShowCompleted] = useState(false);

  useEffect(() => {
    setLoading(true);
    getTasks(showCompleted ? undefined : false)
      .then(setTasks)
      .finally(() => setLoading(false));
  }, [showCompleted]);

  const handleToggle = async (task: TaskData) => {
    const next = !task.completed;
    // 楽観的更新
    setTasks((prev) =>
      prev.map((t) => (t.id === task.id ? { ...t, completed: next } : t))
    );
    try {
      await completeTask(task.id, next);
      if (next) {
        sendEvent({ action: "task_complete", category: "task", label: task.id });
      }
      // 未完了フィルター中は完了したタスクをリストから除去
      if (!showCompleted && next) {
        setTasks((prev) => prev.filter((t) => t.id !== task.id));
      }
    } catch {
      // 失敗時は元に戻す
      setTasks((prev) =>
        prev.map((t) => (t.id === task.id ? { ...t, completed: task.completed } : t))
      );
    }
  };

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        <NavBar />
        <main className="max-w-2xl mx-auto px-4 py-6 pb-nav">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
              タスク
            </h2>
            <label className="flex items-center gap-2 text-sm text-gray-500 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={showCompleted}
                onChange={(e) => setShowCompleted(e.target.checked)}
                className="rounded accent-blue-600"
              />
              完了済みも表示
            </label>
          </div>

          {loading && (
            <div className="flex items-center gap-3 py-8 text-sm text-gray-400">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-200 border-t-blue-400" />
              読み込み中...
            </div>
          )}

          {!loading && tasks.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-16 text-center">
              <div className="w-12 h-12 rounded-2xl bg-gray-100 flex items-center justify-center">
                <svg className="w-6 h-6 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
              </div>
              <p className="text-sm text-gray-400 font-medium">タスクはありません</p>
            </div>
          )}

          <ul className="flex flex-col gap-2">
            {tasks.map((task) => (
              <li
                key={task.id}
                className={`bg-white rounded-2xl border border-gray-100 p-4 flex items-start gap-3 transition-opacity ${
                  task.completed ? "opacity-50" : ""
                }`}
              >
                {/* チェックボックス */}
                <button
                  onClick={() => handleToggle(task)}
                  className={`mt-0.5 h-5 w-5 rounded-full border-2 flex-shrink-0 flex items-center justify-center transition-all ${
                    task.completed
                      ? "bg-emerald-500 border-emerald-500"
                      : "border-gray-300 hover:border-blue-400"
                  }`}
                  aria-label={task.completed ? "未完了に戻す" : "完了にする"}
                >
                  {task.completed && (
                    <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </button>

                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-semibold ${task.completed ? "line-through text-gray-400" : "text-gray-800"}`}>
                    {task.title}
                  </p>
                  <div className="flex flex-wrap gap-x-3 mt-1">
                    {task.due_date && (
                      <p className="text-xs text-gray-400">
                        📅 {task.due_date}
                      </p>
                    )}
                    {task.assignee && (
                      <p className="text-xs text-gray-400">
                        👤 {task.assignee}
                      </p>
                    )}
                  </div>
                  {task.note && (
                    <p className="text-xs text-gray-400 mt-1 line-clamp-2">
                      {task.note}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </main>
      </div>
    </AuthGuard>
  );
}

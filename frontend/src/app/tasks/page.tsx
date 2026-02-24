"use client";

import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { NavBar } from "@/components/NavBar";
import { TaskData, getTasks, completeTask } from "@/lib/api";

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

  const handleToggle = async (task: TaskData & { id?: string }, completed: boolean) => {
    if (!task.id) return;
    await completeTask(task.id, completed);
    setTasks((prev) =>
      prev.filter((t) => (t as TaskData & { id?: string }).id !== task.id)
    );
  };

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        <NavBar />
        <main className="max-w-2xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-700">タスク</h2>
            <label className="flex items-center gap-2 text-sm text-gray-500 cursor-pointer">
              <input
                type="checkbox"
                checked={showCompleted}
                onChange={(e) => setShowCompleted(e.target.checked)}
                className="rounded"
              />
              完了済みも表示
            </label>
          </div>

          {loading && <p className="text-gray-400 text-sm">読み込み中...</p>}

          {!loading && tasks.length === 0 && (
            <p className="text-gray-400 text-sm text-center py-8">
              タスクはありません
            </p>
          )}

          <ul className="flex flex-col gap-2">
            {tasks.map((task) => {
              const t = task as TaskData & { id?: string; completed?: boolean };
              return (
                <li
                  key={t.id}
                  className="bg-white rounded-xl shadow-sm p-4 flex items-start gap-3"
                >
                  <button
                    onClick={() => handleToggle(t, !t.completed)}
                    className={`mt-0.5 h-5 w-5 rounded border-2 flex-shrink-0 ${
                      t.completed
                        ? "bg-green-500 border-green-500"
                        : "border-gray-300 hover:border-blue-400"
                    }`}
                    aria-label={t.completed ? "未完了に戻す" : "完了にする"}
                  >
                    {t.completed && (
                      <span className="text-white text-xs leading-none">✓</span>
                    )}
                  </button>
                  <div className="flex-1 min-w-0">
                    <p
                      className={`text-sm font-medium ${
                        t.completed ? "line-through text-gray-400" : "text-gray-800"
                      }`}
                    >
                      {task.title}
                    </p>
                    {task.due_date && (
                      <p className="text-xs text-gray-400 mt-0.5">
                        期限: {task.due_date}
                      </p>
                    )}
                    {task.assignee && (
                      <p className="text-xs text-gray-400">
                        担当: {task.assignee}
                      </p>
                    )}
                    {task.note && (
                      <p className="text-xs text-gray-400 mt-1 line-clamp-2">
                        {task.note}
                      </p>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </main>
      </div>
    </AuthGuard>
  );
}

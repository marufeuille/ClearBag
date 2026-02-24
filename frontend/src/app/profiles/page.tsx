"use client";

import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { NavBar } from "@/components/NavBar";
import {
  UserProfile,
  getProfiles,
  createProfile,
  updateProfile,
  deleteProfile,
} from "@/lib/api";

const EMPTY_FORM = { name: "", grade: "", keywords: "" };

export default function ProfilesPage() {
  const [profiles, setProfiles] = useState<UserProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<UserProfile | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      setProfiles(await getProfiles());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const startEdit = (profile: UserProfile) => {
    setEditing(profile);
    setForm({
      name: profile.name,
      grade: profile.grade,
      keywords: profile.keywords,
    });
  };

  const startNew = () => {
    setEditing({ id: "", name: "", grade: "", keywords: "" });
    setForm(EMPTY_FORM);
  };

  const cancel = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editing?.id) {
        await updateProfile(editing.id, form);
      } else {
        await createProfile(form);
      }
      await load();
      cancel();
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("このプロフィールを削除しますか？")) return;
    await deleteProfile(id);
    setProfiles((prev) => prev.filter((p) => p.id !== id));
  };

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        <NavBar />
        <main className="max-w-2xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-700">
              子どものプロフィール
            </h2>
            {!editing && (
              <button
                onClick={startNew}
                className="text-sm bg-blue-500 text-white px-3 py-1.5 rounded-lg hover:bg-blue-600"
              >
                + 追加
              </button>
            )}
          </div>

          {editing !== null && (
            <div className="bg-white rounded-2xl shadow-sm p-4 mb-4">
              <h3 className="text-sm font-semibold text-gray-600 mb-3">
                {editing.id ? "プロフィールを編集" : "新しいプロフィール"}
              </h3>
              <form onSubmit={handleSubmit} className="flex flex-col gap-3">
                <div>
                  <label className="text-xs text-gray-500">名前</label>
                  <input
                    className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    required
                    placeholder="例: 太郎"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500">学年</label>
                  <input
                    className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                    value={form.grade}
                    onChange={(e) => setForm({ ...form, grade: e.target.value })}
                    placeholder="例: 小学2年生"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500">
                    キーワード（カンマ区切り）
                  </label>
                  <input
                    className="mt-1 w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                    value={form.keywords}
                    onChange={(e) =>
                      setForm({ ...form, keywords: e.target.value })
                    }
                    placeholder="例: 給食, 体操服, 水泳"
                  />
                </div>
                <div className="flex gap-2 justify-end">
                  <button
                    type="button"
                    onClick={cancel}
                    className="text-sm text-gray-500 px-3 py-1.5 rounded-lg hover:bg-gray-100"
                  >
                    キャンセル
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="text-sm bg-blue-500 text-white px-4 py-1.5 rounded-lg hover:bg-blue-600 disabled:opacity-50"
                  >
                    {saving ? "保存中..." : "保存"}
                  </button>
                </div>
              </form>
            </div>
          )}

          {loading && <p className="text-gray-400 text-sm">読み込み中...</p>}

          {!loading && profiles.length === 0 && !editing && (
            <p className="text-gray-400 text-sm text-center py-8">
              プロフィールがありません
            </p>
          )}

          <ul className="flex flex-col gap-3">
            {profiles.map((p) => (
              <li
                key={p.id}
                className="bg-white rounded-xl shadow-sm p-4 flex items-start justify-between gap-3"
              >
                <div>
                  <p className="font-medium text-gray-800">{p.name}</p>
                  {p.grade && (
                    <p className="text-xs text-gray-500 mt-0.5">{p.grade}</p>
                  )}
                  {p.keywords && (
                    <p className="text-xs text-gray-400 mt-1">{p.keywords}</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => startEdit(p)}
                    className="text-xs text-blue-400 hover:text-blue-600"
                  >
                    編集
                  </button>
                  <button
                    onClick={() => handleDelete(p.id)}
                    className="text-xs text-gray-300 hover:text-red-400"
                  >
                    削除
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </main>
      </div>
    </AuthGuard>
  );
}

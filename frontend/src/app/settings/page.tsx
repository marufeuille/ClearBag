"use client";

import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { NavBar } from "@/components/NavBar";
import { Settings, getSettings, updateSettings } from "@/lib/api";

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getSettings()
      .then(setSettings)
      .finally(() => setLoading(false));
  }, []);

  const handleToggle = async (
    key: "notification_email" | "notification_web_push"
  ) => {
    if (!settings) return;
    const updated = { ...settings, [key]: !settings[key] };
    setSettings(updated);
    setSaving(true);
    try {
      await updateSettings({ [key]: updated[key] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  const copyIcal = () => {
    if (!settings?.ical_url) return;
    navigator.clipboard.writeText(settings.ical_url);
  };

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        <NavBar />
        <main className="max-w-2xl mx-auto px-4 py-6">
          <h2 className="text-lg font-semibold text-gray-700 mb-4">設定</h2>

          {loading && <p className="text-gray-400 text-sm">読み込み中...</p>}

          {settings && (
            <div className="flex flex-col gap-4">
              {/* プラン情報 */}
              <div className="bg-white rounded-2xl shadow-sm p-4">
                <h3 className="text-sm font-semibold text-gray-600 mb-3">
                  プラン
                </h3>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-800">
                      {settings.plan === "premium"
                        ? "プレミアムプラン"
                        : "無料プラン"}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      今月の解析数: {settings.documents_this_month}枚
                      {settings.plan === "free" && " / 5枚"}
                    </p>
                  </div>
                  {settings.plan === "free" && (
                    <span className="text-xs bg-blue-50 text-blue-600 px-3 py-1 rounded-full font-medium">
                      ¥300/月でアップグレード
                    </span>
                  )}
                </div>
              </div>

              {/* iCal フィード */}
              <div className="bg-white rounded-2xl shadow-sm p-4">
                <h3 className="text-sm font-semibold text-gray-600 mb-3">
                  iCal フィード
                </h3>
                <p className="text-xs text-gray-500 mb-2">
                  このURLをカレンダーアプリに登録すると、予定が自動同期されます。
                </p>
                {settings.ical_url ? (
                  <div className="flex gap-2">
                    <input
                      readOnly
                      value={settings.ical_url}
                      className="flex-1 text-xs border border-gray-200 rounded-lg px-3 py-2 bg-gray-50 text-gray-500"
                    />
                    <button
                      onClick={copyIcal}
                      className="text-xs bg-gray-100 text-gray-600 px-3 py-2 rounded-lg hover:bg-gray-200"
                    >
                      コピー
                    </button>
                  </div>
                ) : (
                  <p className="text-xs text-gray-400">
                    URLは自動的に発行されます
                  </p>
                )}
              </div>

              {/* 通知設定 */}
              <div className="bg-white rounded-2xl shadow-sm p-4">
                <h3 className="text-sm font-semibold text-gray-600 mb-3">
                  通知
                </h3>
                <div className="flex flex-col gap-3">
                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="text-sm text-gray-700">メール通知</span>
                    <button
                      onClick={() => handleToggle("notification_email")}
                      disabled={saving}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        settings.notification_email
                          ? "bg-blue-500"
                          : "bg-gray-200"
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                          settings.notification_email
                            ? "translate-x-6"
                            : "translate-x-1"
                        }`}
                      />
                    </button>
                  </label>

                  <label className="flex items-center justify-between cursor-pointer">
                    <span className="text-sm text-gray-700">プッシュ通知</span>
                    <button
                      onClick={() => handleToggle("notification_web_push")}
                      disabled={saving}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        settings.notification_web_push
                          ? "bg-blue-500"
                          : "bg-gray-200"
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                          settings.notification_web_push
                            ? "translate-x-6"
                            : "translate-x-1"
                        }`}
                      />
                    </button>
                  </label>
                </div>

                {saved && (
                  <p className="text-xs text-green-500 mt-2">保存しました</p>
                )}
              </div>
            </div>
          )}
        </main>
      </div>
    </AuthGuard>
  );
}

"use client";

import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { NavBar } from "@/components/NavBar";
import {
  Settings, getSettings, updateSettings,
  FamilyInfo, FamilyMember,
  getFamily, getFamilyMembers, updateFamilyName, inviteMember, removeMember,
} from "@/lib/api";
import {
  isPushSupported,
  getPermissionState,
  subscribePush,
  unsubscribePush,
} from "@/lib/pushSubscription";

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [family, setFamily] = useState<FamilyInfo | null>(null);
  const [members, setMembers] = useState<FamilyMember[]>([]);
  const [familyNameInput, setFamilyNameInput] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteUrl, setInviteUrl] = useState("");
  const [inviting, setInviting] = useState(false);
  const [pushPermission, setPushPermission] = useState<NotificationPermission>("default");
  const [pushSupported, setPushSupported] = useState(true);
  const [pushError, setPushError] = useState<string | null>(null);

  useEffect(() => {
    setPushSupported(isPushSupported());
    setPushPermission(getPermissionState());
    Promise.all([getSettings(), getFamily(), getFamilyMembers()])
      .then(([s, f, m]) => {
        setSettings(s);
        setFamily(f);
        setFamilyNameInput(f.name);
        setMembers(m);
      })
      .finally(() => setLoading(false));
  }, []);

  const handlePushToggle = async () => {
    if (!settings) return;
    setSaving(true);
    setPushError(null);
    try {
      if (!settings.notification_web_push) {
        // ON: Push 許可取得 → バックエンド登録 → 設定更新
        const granted = await subscribePush();
        if (granted) {
          const updated = await updateSettings({ notification_web_push: true });
          setSettings(updated);
          setPushPermission(getPermissionState());
          setSaved(true);
          setTimeout(() => setSaved(false), 2000);
        } else {
          setPushPermission(getPermissionState());
        }
      } else {
        // OFF: Push 解除 → バックエンド削除 → 設定更新
        await unsubscribePush();
        const updated = await updateSettings({ notification_web_push: false });
        setSettings(updated);
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      }
    } catch (e) {
      setPushError(e instanceof Error ? e.message : "通知の設定に失敗しました");
    } finally {
      setSaving(false);
    }
  };

  const handleFamilyNameSave = async () => {
    if (!family) return;
    setSaving(true);
    try {
      const updated = await updateFamilyName(familyNameInput);
      setFamily(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  const handleInvite = async () => {
    if (!inviteEmail) return;
    setInviting(true);
    try {
      const result = await inviteMember(inviteEmail);
      setInviteUrl(result.invite_url);
      setInviteEmail("");
    } finally {
      setInviting(false);
    }
  };

  const handleRemoveMember = async (uid: string, displayName: string) => {
    if (!confirm(`${displayName} をファミリーから削除しますか？`)) return;
    await removeMember(uid);
    setMembers((prev) => prev.filter((m) => m.uid !== uid));
  };

  const copyInviteUrl = () => {
    navigator.clipboard.writeText(inviteUrl);
  };

  const copyIcal = () => {
    if (!settings?.ical_url) return;
    navigator.clipboard.writeText(settings.ical_url);
  };

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        <NavBar />
        <main className="max-w-2xl mx-auto px-4 py-6 pb-nav">
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

              {/* ファミリー管理 */}
              {family && (
                <div className="bg-white rounded-2xl shadow-sm p-4">
                  <h3 className="text-sm font-semibold text-gray-600 mb-3">ファミリー</h3>

                  {/* ファミリー名 */}
                  <div className="mb-4">
                    <p className="text-xs text-gray-500 mb-1">ファミリー名</p>
                    {family.role === "owner" ? (
                      <div className="flex gap-2">
                        <input
                          value={familyNameInput}
                          onChange={(e) => setFamilyNameInput(e.target.value)}
                          className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2"
                        />
                        <button
                          onClick={handleFamilyNameSave}
                          disabled={saving}
                          className="text-xs bg-blue-500 text-white px-3 py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50"
                        >
                          保存
                        </button>
                      </div>
                    ) : (
                      <p className="text-sm text-gray-800">{family.name}</p>
                    )}
                  </div>

                  {/* メンバー一覧 */}
                  <div className="mb-4">
                    <p className="text-xs text-gray-500 mb-2">メンバー</p>
                    <div className="flex flex-col gap-2">
                      {members.map((m) => (
                        <div key={m.uid} className="flex items-center justify-between">
                          <div>
                            <p className="text-sm text-gray-800">
                              {m.display_name || m.email || m.uid}
                            </p>
                            <p className="text-xs text-gray-400">
                              {m.email && m.display_name ? m.email + " · " : ""}
                              {m.role === "owner" ? "オーナー" : "メンバー"}
                            </p>
                          </div>
                          {family.role === "owner" && m.role !== "owner" && (
                            <button
                              onClick={() =>
                                handleRemoveMember(
                                  m.uid,
                                  m.display_name || m.email || m.uid,
                                )
                              }
                              className="text-xs text-red-400 hover:text-red-600"
                            >
                              削除
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 招待（オーナーのみ） */}
                  {family.role === "owner" && (
                    <div>
                      <p className="text-xs text-gray-500 mb-1">メンバーを招待</p>
                      <div className="flex gap-2 mb-2">
                        <input
                          type="email"
                          value={inviteEmail}
                          onChange={(e) => setInviteEmail(e.target.value)}
                          placeholder="メールアドレス"
                          className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2"
                        />
                        <button
                          onClick={handleInvite}
                          disabled={inviting || !inviteEmail}
                          className="text-xs bg-green-500 text-white px-3 py-2 rounded-lg hover:bg-green-600 disabled:opacity-50"
                        >
                          招待
                        </button>
                      </div>
                      {inviteUrl && (
                        <div className="flex gap-2">
                          <input
                            readOnly
                            value={inviteUrl}
                            className="flex-1 text-xs border border-gray-200 rounded-lg px-3 py-2 bg-gray-50 text-gray-500"
                          />
                          <button
                            onClick={copyInviteUrl}
                            className="text-xs bg-gray-100 text-gray-600 px-3 py-2 rounded-lg hover:bg-gray-200"
                          >
                            コピー
                          </button>
                        </div>
                      )}
                    </div>
                  )}

                  {saved && (
                    <p className="text-xs text-green-500 mt-2">保存しました</p>
                  )}
                </div>
              )}

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
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-sm text-gray-700">プッシュ通知</span>
                      {!pushSupported && (
                        <p className="text-xs text-gray-400 mt-0.5">
                          このブラウザはプッシュ通知に対応していません
                        </p>
                      )}
                      {pushSupported && pushPermission === "denied" && (
                        <p className="text-xs text-orange-500 mt-0.5">
                          ブラウザの設定から通知を許可してください
                        </p>
                      )}
                      {pushError && (
                        <p className="text-xs text-red-500 mt-0.5">{pushError}</p>
                      )}
                    </div>
                    <button
                      onClick={handlePushToggle}
                      disabled={saving || !pushSupported || pushPermission === "denied"}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        settings.notification_web_push
                          ? "bg-blue-500"
                          : "bg-gray-200"
                      } disabled:opacity-40`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                          settings.notification_web_push
                            ? "translate-x-6"
                            : "translate-x-1"
                        }`}
                      />
                    </button>
                  </div>
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

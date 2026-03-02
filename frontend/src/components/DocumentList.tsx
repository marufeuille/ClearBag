"use client";

import { useEffect, useState } from "react";
import {
  DocumentRecord,
  DocumentDetail,
  getDocuments,
  getDocumentDetail,
  getDocumentUrl,
  deleteDocument,
} from "@/lib/api";

interface DocumentListProps {
  refreshKey?: number;
}

const STATUS_CONFIG: Record<
  DocumentRecord["status"],
  { label: string; color: string; dot: string }
> = {
  pending:    { label: "待機中",  color: "text-amber-600 bg-amber-50 border-amber-100",   dot: "bg-amber-400" },
  processing: { label: "解析中",  color: "text-blue-600 bg-blue-50 border-blue-100",     dot: "bg-blue-400 animate-pulse" },
  completed:  { label: "完了",    color: "text-emerald-600 bg-emerald-50 border-emerald-100", dot: "bg-emerald-400" },
  error:      { label: "エラー",  color: "text-red-600 bg-red-50 border-red-100",         dot: "bg-red-400" },
};

const CACHE_KEY = "clearbag_docs_cache";

function loadCache(): DocumentRecord[] {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? (JSON.parse(raw) as DocumentRecord[]) : [];
  } catch {
    return [];
  }
}

function saveCache(docs: DocumentRecord[]) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(docs));
  } catch {}
}

function isToday(isoString: string | null): boolean {
  if (!isoString) return false;
  return isoString.slice(0, 10) === new Date().toISOString().slice(0, 10);
}

export function DocumentList({ refreshKey }: DocumentListProps) {
  const [docs, setDocs] = useState<DocumentRecord[]>(() => loadCache());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [details, setDetails] = useState<Record<string, DocumentDetail>>({});
  const [detailLoading, setDetailLoading] = useState<string | null>(null);
  const [urlLoading, setUrlLoading] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDocuments();
      setDocs(data);
      saveCache(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [refreshKey]);

  const handleToggle = async (id: string) => {
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(id);
    if (details[id]) return; // キャッシュ済み

    setDetailLoading(id);
    try {
      const detail = await getDocumentDetail(id);
      setDetails((prev) => ({ ...prev, [id]: detail }));
    } catch {
      // 詳細取得失敗時はアコーディオンは開いたまま（空表示）
    } finally {
      setDetailLoading(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("このドキュメントを削除しますか？")) return;
    setDeletingId(id);
    try {
      await deleteDocument(id);
      setDocs((prev) => {
        const next = prev.filter((d) => d.id !== id);
        saveCache(next);
        return next;
      });
      if (expandedId === id) setExpandedId(null);
    } finally {
      setDeletingId(null);
    }
  };

  const handleViewFile = async (doc: DocumentRecord) => {
    setUrlLoading(doc.id);
    try {
      const { url, mime_type } = await getDocumentUrl(doc.id);
      const previewable = mime_type.startsWith("image/") || mime_type === "application/pdf";
      if (previewable) {
        window.open(url, "_blank", "noopener,noreferrer");
      } else {
        const a = document.createElement("a");
        a.href = url;
        a.download = doc.archive_filename || doc.original_filename;
        a.click();
      }
    } catch {
      // URL 取得失敗時は何もしない
    } finally {
      setUrlLoading(null);
    }
  };

  if (loading && docs.length === 0) {
    return (
      <div className="flex items-center gap-3 px-5 py-8 text-sm text-gray-400">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-200 border-t-blue-400" />
        読み込み中...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-start gap-3 px-5 py-4 text-sm text-red-600">
        <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>取得エラー: {error}</span>
      </div>
    );
  }

  if (docs.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 px-5 py-12 text-center">
        <div className="w-12 h-12 rounded-2xl bg-gray-50 flex items-center justify-center">
          <svg className="w-6 h-6 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <p className="text-sm text-gray-400 font-medium">まだドキュメントがありません</p>
        <p className="text-xs text-gray-300">上からお便りをアップロードしてみましょう</p>
      </div>
    );
  }

  return (
    <ul className="divide-y divide-gray-50">
      {loading && (
        <div className="flex items-center gap-2 px-5 py-2 text-xs text-gray-400 border-b border-gray-50">
          <div className="h-3 w-3 animate-spin rounded-full border border-gray-200 border-t-blue-400" />
          更新中...
        </div>
      )}
      {docs.map((doc) => {
        const cfg = STATUS_CONFIG[doc.status];
        const isExpanded = expandedId === doc.id;
        const detail = details[doc.id];
        const isNew = isToday(doc.created_at);

        return (
          <li key={doc.id} className="divide-y divide-gray-50">
            {/* ── ヘッダー行（クリックで展開/折りたたみ） ── */}
            <button
              type="button"
              onClick={() => handleToggle(doc.id)}
              className="w-full flex items-start gap-3 px-5 py-4 hover:bg-gray-50/60 transition-colors text-left"
              aria-expanded={isExpanded}
            >
              {/* ファイルアイコン */}
              <div className="mt-0.5 w-9 h-9 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              </div>

              {/* コンテンツ */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <p className="text-sm font-semibold text-gray-800 truncate">
                    {doc.archive_filename || doc.original_filename}
                  </p>
                  {isNew && (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                      NEW
                    </span>
                  )}
                </div>
                {doc.summary && (
                  <p className={`text-xs text-gray-500 mt-0.5 leading-relaxed ${isExpanded ? "" : "line-clamp-2"}`}>
                    {doc.summary}
                  </p>
                )}
                {doc.error_message && (
                  <p className="text-xs text-red-500 mt-0.5">{doc.error_message}</p>
                )}
              </div>

              {/* ステータス + シェブロン + 削除 */}
              <div className="flex items-center gap-2 flex-shrink-0 mt-0.5">
                <span className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-medium border ${cfg.color}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
                  {cfg.label}
                </span>
                <svg
                  className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                  fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); handleDelete(doc.id); }}
                  disabled={deletingId === doc.id}
                  className="w-7 h-7 flex items-center justify-center rounded-lg text-gray-300 hover:text-red-400 hover:bg-red-50 transition-all disabled:opacity-40"
                  aria-label="削除"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </button>

            {/* ── 展開パネル ── */}
            {isExpanded && (
              <div className="px-5 py-4 bg-gray-50/40 space-y-4">
                {detailLoading === doc.id ? (
                  <div className="flex items-center gap-2 text-xs text-gray-400">
                    <div className="h-3 w-3 animate-spin rounded-full border border-gray-200 border-t-blue-400" />
                    読み込み中...
                  </div>
                ) : (
                  <>
                    {/* カテゴリバッジ */}
                    {doc.category && (
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-400">カテゴリ:</span>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 font-medium">
                          {doc.category}
                        </span>
                      </div>
                    )}

                    {/* 関連イベント */}
                    {detail && detail.events.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-gray-500 mb-1.5">関連イベント</p>
                        <ul className="space-y-1">
                          {detail.events.map((ev, i) => (
                            <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                              <svg className="w-3.5 h-3.5 mt-0.5 text-blue-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                              </svg>
                              <span>
                                <span className="text-gray-400">{ev.start.slice(0, 10)}</span>
                                {" "}{ev.summary}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* 関連タスク */}
                    {detail && detail.tasks.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-gray-500 mb-1.5">関連タスク</p>
                        <ul className="space-y-1">
                          {detail.tasks.map((task, i) => (
                            <li key={i} className="flex items-start gap-2 text-xs text-gray-600">
                              <svg className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${task.completed ? "text-emerald-400" : "text-amber-400"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                {task.completed
                                  ? <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                  : <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                }
                              </svg>
                              <span className={task.completed ? "line-through text-gray-400" : ""}>
                                <span className="text-gray-400">{task.due_date}</span>
                                {" "}{task.title}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* イベント・タスクなし */}
                    {detail && detail.events.length === 0 && detail.tasks.length === 0 && (
                      <p className="text-xs text-gray-400">関連するイベント・タスクはありません</p>
                    )}

                    {/* 元ファイルを表示ボタン */}
                    <div className="pt-1">
                      <button
                        type="button"
                        onClick={() => handleViewFile(doc)}
                        disabled={urlLoading === doc.id}
                        className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-white border border-gray-200 text-gray-600 hover:bg-gray-50 hover:text-blue-600 hover:border-blue-200 transition-all disabled:opacity-40"
                        data-testid="view-file-button"
                      >
                        {urlLoading === doc.id ? (
                          <div className="h-3 w-3 animate-spin rounded-full border border-gray-300 border-t-blue-400" />
                        ) : (
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                        )}
                        元ファイルを表示
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}

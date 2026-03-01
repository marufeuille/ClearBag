"use client";

import { useEffect, useState } from "react";
import { DocumentRecord, getDocuments, deleteDocument } from "@/lib/api";

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

export function DocumentList({ refreshKey }: DocumentListProps) {
  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDocuments();
      setDocs(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [refreshKey]);

  const handleDelete = async (id: string) => {
    if (!confirm("このドキュメントを削除しますか？")) return;
    setDeletingId(id);
    try {
      await deleteDocument(id);
      setDocs((prev) => prev.filter((d) => d.id !== id));
    } finally {
      setDeletingId(null);
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
        return (
          <li
            key={doc.id}
            className="flex items-start gap-3 px-5 py-4 hover:bg-gray-50/60 transition-colors"
          >
            {/* ファイルアイコン */}
            <div className="mt-0.5 w-9 h-9 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
              <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
            </div>

            {/* コンテンツ */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-gray-800 truncate">
                {doc.archive_filename || doc.original_filename}
              </p>
              {doc.summary && (
                <p className="text-xs text-gray-500 mt-0.5 line-clamp-2 leading-relaxed">
                  {doc.summary}
                </p>
              )}
              {doc.error_message && (
                <p className="text-xs text-red-500 mt-0.5">{doc.error_message}</p>
              )}
            </div>

            {/* ステータス + 削除 */}
            <div className="flex items-center gap-2 flex-shrink-0 mt-0.5">
              <span className={`inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-medium border ${cfg.color}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
                {cfg.label}
              </span>
              <button
                onClick={() => handleDelete(doc.id)}
                disabled={deletingId === doc.id}
                className="w-7 h-7 flex items-center justify-center rounded-lg text-gray-300 hover:text-red-400 hover:bg-red-50 transition-all disabled:opacity-40"
                aria-label="削除"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

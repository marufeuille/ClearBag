"use client";

import { useEffect, useState } from "react";
import { DocumentRecord, getDocuments, deleteDocument } from "@/lib/api";

interface DocumentListProps {
  refreshKey?: number;
}

const STATUS_LABEL: Record<DocumentRecord["status"], string> = {
  pending: "待機中",
  processing: "解析中",
  completed: "完了",
  error: "エラー",
};

const STATUS_COLOR: Record<DocumentRecord["status"], string> = {
  pending: "text-yellow-600 bg-yellow-50",
  processing: "text-blue-600 bg-blue-50",
  completed: "text-green-600 bg-green-50",
  error: "text-red-600 bg-red-50",
};

export function DocumentList({ refreshKey }: DocumentListProps) {
  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await getDocuments();
      setDocs(data);
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

  if (loading) {
    return <p className="text-gray-400 text-sm">読み込み中...</p>;
  }

  if (docs.length === 0) {
    return (
      <p className="text-gray-400 text-sm text-center py-4">
        まだドキュメントがありません
      </p>
    );
  }

  return (
    <ul className="divide-y divide-gray-100">
      {docs.map((doc) => (
        <li key={doc.id} className="py-3 flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-800 truncate">
              {doc.original_filename}
            </p>
            {doc.summary && (
              <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                {doc.summary}
              </p>
            )}
            {doc.error_message && (
              <p className="text-xs text-red-500 mt-0.5">{doc.error_message}</p>
            )}
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <span
              className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLOR[doc.status]}`}
            >
              {STATUS_LABEL[doc.status]}
            </span>
            <button
              onClick={() => handleDelete(doc.id)}
              disabled={deletingId === doc.id}
              className="text-gray-300 hover:text-red-400 text-xs"
              aria-label="削除"
            >
              ✕
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}

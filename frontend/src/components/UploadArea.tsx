/**
 * アップロードエリアコンポーネント
 *
 * カメラ撮影（navigator.mediaDevices）とドラッグ&ドロップ・
 * ファイル選択の両方に対応する。
 */

"use client";

import { useRef, useState } from "react";
import { uploadDocument } from "@/lib/api";

interface UploadAreaProps {
  onUploaded?: (documentId: string) => void;
  onError?: (error: string) => void;
}

export function UploadArea({ onUploaded, onError }: UploadAreaProps) {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    if (!file) return;

    const allowed = [
      "application/pdf",
      "image/jpeg",
      "image/png",
      "image/webp",
      "image/heic",
    ];
    if (!allowed.includes(file.type)) {
      onError?.("PDF または画像ファイル（JPG / PNG / WebP / HEIC）を選択してください");
      return;
    }

    setUploading(true);
    try {
      const result = await uploadDocument(file);
      onUploaded?.(result.id);
    } catch (e) {
      const msg =
        e instanceof Error && e.message === "FREE_LIMIT_EXCEEDED"
          ? "無料プランの月間上限（5枚）に達しました。プレミアムプランへのアップグレードをご検討ください。"
          : "アップロードに失敗しました。もう一度お試しください。";
      onError?.(msg);
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  return (
    <div
      className={`relative rounded-2xl border-2 border-dashed p-8 transition-all cursor-pointer ${
        dragOver
          ? "border-blue-400 bg-blue-50 scale-[1.01]"
          : "border-gray-200 bg-white hover:border-blue-300 hover:bg-blue-50/30"
      }`}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      onClick={() => !uploading && fileInputRef.current?.click()}
    >
      {uploading ? (
        <div className="flex flex-col items-center gap-3 py-4">
          <div className="relative">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-blue-100 border-t-blue-500" />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="h-5 w-5 rounded-full bg-blue-50" />
            </div>
          </div>
          <p className="text-sm font-medium text-blue-600">解析キューに登録中...</p>
          <p className="text-xs text-gray-400">しばらくお待ちください</p>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-4">
          {/* アップロードアイコン */}
          <div className="w-14 h-14 rounded-2xl bg-blue-50 flex items-center justify-center">
            <svg className="w-7 h-7 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
          </div>

          <div className="text-center">
            <p className="text-sm font-semibold text-gray-700">
              お便りをドラッグ&ドロップ
            </p>
            <p className="text-xs text-gray-400 mt-1">
              または下のボタンからアップロード
            </p>
          </div>

          {/* ボタン群 */}
          <div className="flex gap-3" onClick={(e) => e.stopPropagation()}>
            <button
              className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm shadow-blue-200 hover:bg-blue-700 active:scale-95 transition-all"
              onClick={() => cameraInputRef.current?.click()}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              カメラ
            </button>

            <button
              className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm font-semibold text-gray-600 hover:bg-gray-50 active:scale-95 transition-all"
              onClick={() => fileInputRef.current?.click()}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
              ファイル
            </button>
          </div>

          <p className="text-xs text-gray-400">
            PDF · JPG · PNG · WebP · HEIC
          </p>
        </div>
      )}

      {/* hidden inputs */}
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
      />
      <input
        ref={fileInputRef}
        type="file"
        accept="application/pdf,image/jpeg,image/png,image/webp,image/heic"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
      />
    </div>
  );
}

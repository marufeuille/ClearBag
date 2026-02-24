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

    // 許可するファイル形式
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
      className={`relative flex flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed p-8 transition-colors ${
        dragOver
          ? "border-blue-400 bg-blue-50"
          : "border-gray-300 bg-white hover:border-blue-300"
      }`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
    >
      {uploading ? (
        <div className="flex flex-col items-center gap-2">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
          <p className="text-sm text-gray-500">解析キューに登録中...</p>
        </div>
      ) : (
        <>
          <div className="text-4xl">📄</div>
          <p className="text-center text-gray-600">
            お便りをドラッグ&ドロップ
            <br />
            または下のボタンから選択
          </p>

          <div className="flex gap-3">
            {/* カメラ撮影ボタン */}
            <button
              className="rounded-lg bg-blue-500 px-4 py-2 text-white hover:bg-blue-600"
              onClick={() => cameraInputRef.current?.click()}
            >
              📷 カメラで撮影
            </button>

            {/* ファイル選択ボタン */}
            <button
              className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50"
              onClick={() => fileInputRef.current?.click()}
            >
              📁 ファイルを選択
            </button>
          </div>

          {/* カメラ入力（モバイル: 背面カメラ優先） */}
          <input
            ref={cameraInputRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />

          {/* ファイル選択入力 */}
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,image/jpeg,image/png,image/webp,image/heic"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />

          <p className="text-xs text-gray-400">
            対応形式: PDF / JPG / PNG / WebP / HEIC
          </p>
        </>
      )}
    </div>
  );
}

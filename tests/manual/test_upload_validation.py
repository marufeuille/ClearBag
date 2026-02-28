#!/usr/bin/env python3
"""
アップロードバリデーション 手動検証スクリプト

デプロイ後の dev/prod 環境で、ファイルサイズ・PDF ページ数制限が
正常に機能しているか確認する。

検証シナリオ:
  [1] 通常 PDF    (1ページ, ~1KB)   → 202 Accepted          ← 通ってほしい
  [2] サイズ超過  (11MB ダミー)      → 413 Too Large         ← 弾いてほしい
  [3] ページ数超過 (4ページ PDF)     → 422 Unprocessable     ← 弾いてほしい
  [4] 破損 PDF    (不正バイト列)     → 422 Unprocessable     ← 弾いてほしい

使い方:
  API_URL=https://api.clearbag-dev.example.com \\
  FIREBASE_TOKEN=eyJhbGciO... \\
  uv run python tests/manual/test_upload_validation.py

  # fixtures/ の実ファイルを使いたい場合:
  USE_FIXTURES=1 \\
  API_URL=https://... FIREBASE_TOKEN=... \\
  uv run python tests/manual/test_upload_validation.py

環境変数:
  API_URL        - dev API のベース URL（末尾スラッシュなし）
                   例: https://api-xxxxxxxxxxx-an.a.run.app
  FIREBASE_TOKEN - Firebase ID トークン（取得手順は UPLOAD_VALIDATION_GUIDE.md 参照）
  USE_FIXTURES   - 1 を指定すると tests/manual/fixtures/ のファイルを読み込んで使用
  DISABLE_CLEANUP - 1 を指定すると 202 で登録したドキュメントを削除しない（デフォルト: 削除する）
"""

from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path

import httpx
from pypdf import PdfWriter

# ───────────────────────────────────────────────
# 設定
# ───────────────────────────────────────────────
API_URL = os.environ.get("API_URL", "").rstrip("/")
FIREBASE_TOKEN = os.environ.get("FIREBASE_TOKEN", "")
USE_FIXTURES = os.environ.get("USE_FIXTURES") == "1"
DISABLE_CLEANUP = os.environ.get("DISABLE_CLEANUP") == "1"

FIXTURES_DIR = Path(__file__).parent / "fixtures"

PASS = "✅"
FAIL = "❌"
SKIP = "⏭️"


# ───────────────────────────────────────────────
# テストデータ生成
# ───────────────────────────────────────────────

def _make_pdf_bytes(num_pages: int) -> bytes:
    """pypdf で num_pages ページの空白 PDF を生成する"""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=595, height=842)  # A4
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _load_or_generate(fixture_name: str, generator_fn) -> bytes:
    """USE_FIXTURES=1 なら fixtures/ から読み込み、そうでなければ生成する"""
    if USE_FIXTURES:
        path = FIXTURES_DIR / fixture_name
        if not path.exists():
            print(f"  ⚠️  {path} が見つかりません。プログラム生成に切り替えます。")
        else:
            return path.read_bytes()
    return generator_fn()


# ───────────────────────────────────────────────
# HTTP ヘルパー
# ───────────────────────────────────────────────

def _upload(client: httpx.Client, filename: str, content: bytes, mime_type: str) -> tuple[int, dict]:
    resp = client.post(
        f"{API_URL}/api/documents/upload",
        files={"file": (filename, content, mime_type)},
        timeout=30,
    )
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text}
    return resp.status_code, body


def _delete(client: httpx.Client, doc_id: str) -> None:
    try:
        client.delete(f"{API_URL}/api/documents/{doc_id}", timeout=10)
    except Exception:
        pass


# ───────────────────────────────────────────────
# 各シナリオ
# ───────────────────────────────────────────────

def scenario_normal_pdf(client: httpx.Client) -> bool:
    """[1] 通常 PDF (1ページ) → 202"""
    content = _load_or_generate("valid_1page.pdf", lambda: _make_pdf_bytes(1))
    status, body = _upload(client, "valid_1page.pdf", content, "application/pdf")
    ok = status == 202
    print(f"  {PASS if ok else FAIL} status={status}  期待=202")
    if not ok:
        print(f"     response: {body}")
    # 成功したドキュメントはクリーンアップ
    if ok and not DISABLE_CLEANUP and "id" in body:
        _delete(client, body["id"])
        print(f"     → doc_id={body['id']} を削除しました（クリーンアップ）")
    return ok


def scenario_size_over(client: httpx.Client) -> bool:
    """[2] サイズ超過 (11MB) → 413"""
    print("  （11MB ダミーファイルをメモリ上で生成中...）")
    content = b"\x00" * (11 * 1024 * 1024)
    status, body = _upload(client, "over_limit_11mb.bin", content, "application/pdf")
    ok = status == 413
    print(f"  {PASS if ok else FAIL} status={status}  期待=413")
    if not ok:
        print(f"     response: {body}")
    return ok


def scenario_page_over(client: httpx.Client) -> bool:
    """[3] ページ数超過 (4ページ) → 422"""
    content = _load_or_generate("over_limit_4page.pdf", lambda: _make_pdf_bytes(4))
    status, body = _upload(client, "over_limit_4page.pdf", content, "application/pdf")
    ok = status == 422
    print(f"  {PASS if ok else FAIL} status={status}  期待=422")
    if not ok:
        print(f"     response: {body}")
    return ok


def scenario_corrupted_pdf(client: httpx.Client) -> bool:
    """[4] 破損 PDF → 422"""
    corrupted_path = FIXTURES_DIR / "corrupted.pdf"
    if USE_FIXTURES and corrupted_path.exists():
        content = corrupted_path.read_bytes()
    else:
        content = b"%PDF-1.4\n%%EOF\ncorrupted garbage data that pypdf cannot parse"
    status, body = _upload(client, "corrupted.pdf", content, "application/pdf")
    ok = status == 422
    print(f"  {PASS if ok else FAIL} status={status}  期待=422")
    if not ok:
        print(f"     response: {body}")
    return ok


# ───────────────────────────────────────────────
# メイン
# ───────────────────────────────────────────────

def main() -> None:
    # 前提チェック
    errors = []
    if not API_URL:
        errors.append("API_URL が未設定です")
    if not FIREBASE_TOKEN:
        errors.append("FIREBASE_TOKEN が未設定です（取得手順は UPLOAD_VALIDATION_GUIDE.md 参照）")
    if errors:
        for e in errors:
            print(f"❌ {e}")
        sys.exit(1)

    print("=" * 55)
    print("  アップロードバリデーション 手動検証")
    print("=" * 55)
    print(f"  API_URL     : {API_URL}")
    print(f"  USE_FIXTURES: {USE_FIXTURES}")
    print(f"  token       : {FIREBASE_TOKEN[:20]}...")
    print("=" * 55)

    headers = {"Authorization": f"Bearer {FIREBASE_TOKEN}"}

    results: list[bool] = []
    with httpx.Client(headers=headers) as client:

        print("\n[1/4] 通常 PDF (1ページ, ~1KB) → 202 期待")
        results.append(scenario_normal_pdf(client))
        time.sleep(0.5)

        print("\n[2/4] サイズ超過 (11MB) → 413 期待")
        results.append(scenario_size_over(client))
        time.sleep(0.5)

        print("\n[3/4] ページ数超過 (4ページ) → 422 期待")
        results.append(scenario_page_over(client))
        time.sleep(0.5)

        print("\n[4/4] 破損 PDF → 422 期待")
        results.append(scenario_corrupted_pdf(client))

    # サマリ
    passed = sum(results)
    total = len(results)
    print("\n" + "=" * 55)
    if passed == total:
        print(f"  {PASS} 全シナリオ通過: {passed}/{total}")
    else:
        print(f"  {FAIL} 失敗あり: {passed}/{total} passed")
        failed_indices = [i + 1 for i, ok in enumerate(results) if not ok]
        print(f"     失敗したシナリオ: {failed_indices}")
    print("=" * 55)

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()

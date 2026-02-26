/**
 * ダッシュボード更新テスト
 *
 * ファイルアップロード後にドキュメント一覧が正しく更新されることを確認する。
 * - 初期状態: ドキュメントなし
 * - ファイルアップロード → 成功メッセージ表示
 * - ドキュメント一覧が自動更新 → アップロードしたファイルが表示される
 */
import { test, expect } from "@playwright/test";

test("ファイルアップロード後にドキュメント一覧が更新される", async ({
  page,
}) => {
  let uploadCalled = false;

  // GET /api/documents: アップロード前は空、アップロード後はファイルを返す
  await page.route("**/api/documents", async (route) => {
    if (uploadCalled) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "doc-e2e-1",
            status: "pending",
            original_filename: "school-notice.pdf",
            mime_type: "application/pdf",
            summary: "",
            category: "",
            error_message: null,
          },
        ]),
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: "[]",
      });
    }
  });

  // POST /api/documents/upload: 成功レスポンスを返す
  await page.route("**/api/documents/upload", async (route) => {
    uploadCalled = true;
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({ id: "doc-e2e-1", status: "pending" }),
    });
  });

  await page.goto("/dashboard");

  // 初期状態: ドキュメントがないことを確認
  await expect(page.getByText("まだドキュメントがありません")).toBeVisible();

  // ファイル選択 input に直接ファイルをセット（PDF 用 hidden input）
  const fileInput = page.locator('input[type="file"][accept*="pdf"]');
  await fileInput.setInputFiles({
    name: "school-notice.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 fake content"),
  });

  // 成功メッセージが表示されること
  await expect(
    page.getByText("解析キューに登録しました。数分後に結果が表示されます。")
  ).toBeVisible();

  // ドキュメント一覧が更新され、ファイル名と「待機中」ステータスが表示されること
  await expect(page.getByText("school-notice.pdf")).toBeVisible();
  await expect(page.getByText("待機中")).toBeVisible();
});

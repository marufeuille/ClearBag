/**
 * ダッシュボード更新テスト
 *
 * ファイルアップロード後にドキュメント一覧が正しく更新されることを確認する。
 * - 初期状態: ドキュメントなし
 * - ファイルアップロード → 成功メッセージ表示
 * - ドキュメント一覧が自動更新 → アップロードしたファイルが表示される
 * - サイズ制限超過 → クライアント/サーバー側それぞれでエラーメッセージ表示
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
            archive_filename: "",
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

test("archive_filename が設定されている場合は original_filename の代わりに表示される", async ({
  page,
}) => {
  await page.route("**/api/documents", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "doc-e2e-2",
          status: "completed",
          original_filename: "IMG_1234.jpg",
          archive_filename: "20251025_遠足_長男.pdf",
          mime_type: "image/jpeg",
          summary: "遠足のお知らせ",
          category: "EVENT",
          error_message: null,
        },
      ]),
    });
  });

  await page.goto("/dashboard");

  // archive_filename が優先表示される
  await expect(page.getByText("20251025_遠足_長男.pdf")).toBeVisible();
  // original_filename は表示されない
  await expect(page.getByText("IMG_1234.jpg")).not.toBeVisible();
});

test("クライアント側: 10MB 超のファイルはアップロード前にエラーになる", async ({
  page,
}) => {
  // API へのリクエストは飛ばないことを確認するためにルートをセット
  await page.route("**/api/documents", (route) =>
    route.fulfill({ status: 200, body: "[]" })
  );
  await page.route("**/api/documents/upload", (route) =>
    route.fulfill({ status: 200, body: "{}" })
  );

  await page.goto("/dashboard");

  // 11MB のダミーバッファを作成してファイル選択 input に直接セット
  const fileInput = page.locator('input[type="file"][accept*="pdf"]');
  await fileInput.setInputFiles({
    name: "huge-file.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.alloc(11 * 1024 * 1024),
  });

  // クライアント側バリデーションでエラーメッセージが表示される
  await expect(
    page.getByText("ファイルサイズが上限（10MB）を超えています。")
  ).toBeVisible();
});

test("ドキュメント行をクリックするとアコーディオンが展開される", async ({
  page,
}) => {
  const today = new Date().toISOString();

  await page.route("**/api/documents", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "doc-accordion-1",
          status: "completed",
          original_filename: "test.pdf",
          archive_filename: "20251025_遠足_長男.pdf",
          mime_type: "application/pdf",
          summary: "遠足のお知らせです。持ち物は弁当・水筒・帽子。",
          category: "EVENT",
          error_message: null,
          created_at: today,
        },
      ]),
    });
  });

  await page.route("**/api/documents/doc-accordion-1/detail", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        events: [
          {
            summary: "遠足",
            start: "2025-10-25",
            end: "2025-10-25",
            location: "動物園",
            description: "",
            confidence: "HIGH",
          },
        ],
        tasks: [
          {
            id: "task-1",
            title: "同意書の提出",
            due_date: "2025-10-10",
            assignee: "PARENT",
            note: "",
            completed: false,
          },
        ],
      }),
    });
  });

  await page.goto("/dashboard");

  // ドキュメントが表示されていること
  await expect(page.getByText("20251025_遠足_長男.pdf")).toBeVisible();

  // NEW バッジが表示されていること（created_at が当日）
  await expect(page.getByText("NEW")).toBeVisible();

  // 初期状態: アコーディオン内容は非表示
  await expect(page.getByText("関連イベント")).not.toBeVisible();

  // ドキュメント行をクリック
  await page.getByRole("button", { name: /20251025_遠足_長男/ }).click();

  // 展開後: イベント・タスク・元ファイルボタンが表示される
  await expect(page.getByText("関連イベント")).toBeVisible();
  // イベントタイトルは日付+タイトルの形式で表示される ("2025-10-25 遠足")
  await expect(page.getByText(/2025-10-25.*遠足/)).toBeVisible();
  await expect(page.getByText("関連タスク")).toBeVisible();
  await expect(page.getByText("同意書の提出")).toBeVisible();
  await expect(page.getByTestId("view-file-button")).toBeVisible();

  // 再クリックで折りたたみ
  await page.getByRole("button", { name: /20251025_遠足_長男/ }).click();
  await expect(page.getByText("関連イベント")).not.toBeVisible();
});

test("「元ファイルを表示」ボタンが展開パネル内に表示される", async ({
  page,
}) => {
  await page.route("**/api/documents", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "doc-url-1",
          status: "completed",
          original_filename: "test.pdf",
          archive_filename: "",
          mime_type: "application/pdf",
          summary: "テスト",
          category: "INFO",
          error_message: null,
          created_at: null,
        },
      ]),
    });
  });

  await page.route("**/api/documents/doc-url-1/detail", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ events: [], tasks: [] }),
    });
  });

  await page.goto("/dashboard");

  // アコーディオン展開
  await page.getByRole("button", { name: /test\.pdf/ }).click();

  // 「元ファイルを表示」ボタンが表示される
  await expect(page.getByTestId("view-file-button")).toBeVisible();
});

test("サーバー側: 413 レスポンス時にサイズ超過エラーが表示される", async ({
  page,
}) => {
  await page.route("**/api/documents", (route) =>
    route.fulfill({ status: 200, body: "[]" })
  );

  // サーバーが 413 を返すシナリオをモック
  await page.route("**/api/documents/upload", (route) =>
    route.fulfill({
      status: 413,
      contentType: "application/json",
      body: JSON.stringify({
        detail: "ファイルサイズが上限（10MB）を超えています。",
      }),
    })
  );

  await page.goto("/dashboard");

  const fileInput = page.locator('input[type="file"][accept*="pdf"]');
  await fileInput.setInputFiles({
    name: "test.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 fake content"),
  });

  // サーバーの detail メッセージがそのまま表示される
  await expect(
    page.getByText("ファイルサイズが上限（10MB）を超えています。")
  ).toBeVisible();
});

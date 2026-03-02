/**
 * Web Share Target E2E テスト
 *
 * OS 共有メニューの起動は自動テスト不可のため、以下の戦略でテストする:
 *   1. page.addInitScript() で Cache API にファイルを事前セット
 *   2. ?shared=true でダッシュボードに遷移
 *   3. useShareTarget hook がキャッシュを読み取り、uploadDocument() を呼ぶことを確認
 *
 * テストケース:
 *   - 共有ファイルが自動アップロードされる（成功フロー）
 *   - ?share_error=no_file でエラーメッセージが表示される
 *   - キャッシュのタイムスタンプが期限切れの場合はエラーが表示される
 */

import { test, expect } from "@playwright/test";

const CACHE_NAME = "clearbag-share-target";
const CACHE_KEY = "/share-target-file";

/** Cache API にダミーファイルを書き込むスクリプト */
function makeCacheSetupScript(
  content: string,
  filename: string,
  mimeType: string,
  timestampMs: number
): string {
  return `
    (async () => {
      const cache = await caches.open("${CACHE_NAME}");
      const blob = new Blob([${JSON.stringify(content)}], { type: "${mimeType}" });
      const headers = new Headers({
        "Content-Type": "${mimeType}",
        "X-Share-Target-Filename": encodeURIComponent("${filename}"),
        "X-Share-Target-Timestamp": "${timestampMs}",
      });
      await cache.put("${CACHE_KEY}", new Response(blob, { headers }));
    })();
  `;
}

/** 全 API モック（smoke テストと同じセット） */
async function mockAllApis(
  page: import("@playwright/test").Page,
  uploadCallbacks?: { onUpload?: () => void }
) {
  await page.route("**/api/documents", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    })
  );
  await page.route("**/api/families/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "family-1",
        name: "テストファミリー",
        plan: "free",
        documents_this_month: 0,
        role: "owner",
      }),
    })
  );
  await page.route("**/api/documents/upload", (route) => {
    uploadCallbacks?.onUpload?.();
    return route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({ id: "shared-doc-1", status: "pending" }),
    });
  });
}

test("共有ファイルが自動アップロードされ成功メッセージが表示される", async ({
  page,
}) => {
  let uploadCalled = false;

  await mockAllApis(page, { onUpload: () => { uploadCalled = true; } });

  // Cache API に有効なファイルを事前セット（現在時刻でタイムスタンプ）
  await page.addInitScript(
    makeCacheSetupScript(
      "%PDF-1.4 test content",
      "school-notice.pdf",
      "application/pdf",
      Date.now()
    )
  );

  // ?shared=true でダッシュボードに遷移
  await page.goto("/dashboard/?shared=true");

  // 成功メッセージが表示されること
  await expect(
    page.getByText("共有ファイルを解析キューに登録しました。数分後に結果が表示されます。")
  ).toBeVisible({ timeout: 10000 });

  // upload API が呼ばれたこと
  expect(uploadCalled).toBe(true);
});

test("?share_error=no_file でエラーメッセージが表示される", async ({
  page,
}) => {
  await mockAllApis(page);

  await page.goto("/dashboard/?share_error=no_file");

  await expect(
    page.getByText("共有されたファイルを受け取れませんでした。")
  ).toBeVisible({ timeout: 10000 });
});

test("?share_error=failed でエラーメッセージが表示される", async ({
  page,
}) => {
  await mockAllApis(page);

  await page.goto("/dashboard/?share_error=failed");

  await expect(
    page.getByText("ファイルの共有処理中にエラーが発生しました。")
  ).toBeVisible({ timeout: 10000 });
});

test("キャッシュのタイムスタンプが期限切れの場合はエラーが表示される", async ({
  page,
}) => {
  let uploadCalled = false;

  await mockAllApis(page, { onUpload: () => { uploadCalled = true; } });

  // 10分前のタイムスタンプ（TTL 5分を超過）
  const expiredTimestamp = Date.now() - 10 * 60 * 1000;
  await page.addInitScript(
    makeCacheSetupScript(
      "%PDF-1.4 expired content",
      "old-file.pdf",
      "application/pdf",
      expiredTimestamp
    )
  );

  await page.goto("/dashboard/?shared=true");

  await expect(
    page.getByText("共有ファイルの有効期限が切れました。再度共有してください。")
  ).toBeVisible({ timeout: 10000 });

  // アップロードは呼ばれないこと
  expect(uploadCalled).toBe(false);
});

test("共有完了後に URL パラメータが削除される", async ({ page }) => {
  await mockAllApis(page);

  await page.addInitScript(
    makeCacheSetupScript(
      "%PDF-1.4 test",
      "notice.pdf",
      "application/pdf",
      Date.now()
    )
  );

  await page.goto("/dashboard/?shared=true");

  // 成功メッセージ表示を待つ
  await expect(
    page.getByText("共有ファイルを解析キューに登録しました。数分後に結果が表示されます。")
  ).toBeVisible({ timeout: 10000 });

  // URL パラメータが除去されていること
  expect(page.url()).not.toContain("shared=true");
});

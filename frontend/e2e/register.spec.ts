/**
 * /register ページのテスト
 *
 * - コードなし: エラーメッセージ表示
 * - 有効コード + E2E 自動ログイン: 登録成功 → ダッシュボードリダイレクト
 * - 無効コード (404): エラー表示
 * - 期限切れコード (400 CODE_EXPIRED): エラー表示
 * - 上限超過コード (400 CODE_EXHAUSTED): エラー表示
 */
import { test, expect } from "@playwright/test";

test.describe("/register ページ", () => {
  test("コードなしでアクセスすると無効メッセージが表示される", async ({
    page,
  }) => {
    await page.goto("/register");
    await expect(page.getByText("無効な招待コードです")).toBeVisible();
  });

  test("有効なコードで登録成功しダッシュボードにリダイレクトされる", async ({
    page,
  }) => {
    await page.route("**/api/auth/register", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          activated: true,
          message: "登録が完了しました。ダッシュボードへ移動します。",
        }),
      })
    );

    await page.goto("/register?code=SPRING2026");
    await expect(page.getByText("登録完了")).toBeVisible();
    await page.waitForURL("**/dashboard**", { timeout: 5000 });
  });

  test("無効なコード (404) でエラーメッセージが表示される", async ({
    page,
  }) => {
    await page.route("**/api/auth/register", (route) =>
      route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: "INVALID_CODE" }),
      })
    );

    await page.goto("/register?code=BADCODE");
    await expect(page.getByText("この招待コードは無効です")).toBeVisible();
  });

  test("期限切れコード (400 CODE_EXPIRED) でエラーメッセージが表示される", async ({
    page,
  }) => {
    await page.route("**/api/auth/register", (route) =>
      route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({ detail: "CODE_EXPIRED" }),
      })
    );

    await page.goto("/register?code=OLDCODE");
    await expect(page.getByText("有効期限が切れています")).toBeVisible();
  });

  test("上限超過コード (400 CODE_EXHAUSTED) でエラーメッセージが表示される", async ({
    page,
  }) => {
    await page.route("**/api/auth/register", (route) =>
      route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({ detail: "CODE_EXHAUSTED" }),
      })
    );

    await page.goto("/register?code=FULLCODE");
    await expect(page.getByText("上限に達しました")).toBeVisible();
  });
});

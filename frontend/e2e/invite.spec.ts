/**
 * /invite ページのテスト
 *
 * - トークンなし: 無効メッセージ表示
 * - 有効トークン + E2E 自動ログイン: 参加成功 → ダッシュボードリダイレクト
 * - 無効トークン (404): エラー表示
 * - 使用済みトークン (400): エラー表示
 */
import { test, expect } from "@playwright/test";

test.describe("/invite ページ", () => {
  test("トークンなしでアクセスすると無効メッセージが表示される", async ({
    page,
  }) => {
    await page.goto("/invite");
    await expect(page.getByText("無効な招待リンクです")).toBeVisible();
  });

  test("有効なトークンで参加成功しダッシュボードにリダイレクトされる", async ({
    page,
  }) => {
    await page.route("**/api/families/join", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          family_id: "family-1",
          name: "テストファミリー",
          role: "member",
        }),
      })
    );

    await page.goto("/invite?token=valid-token");
    await expect(
      page.getByText("「テストファミリー」に参加しました")
    ).toBeVisible();
    await page.waitForURL("**/dashboard**", { timeout: 5000 });
  });

  test("無効なトークン (404) でエラーメッセージが表示される", async ({
    page,
  }) => {
    await page.route("**/api/families/join", (route) =>
      route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Invalid invitation token" }),
      })
    );

    await page.goto("/invite?token=invalid-token");
    await expect(page.getByText("この招待リンクは無効です")).toBeVisible();
  });

  test("使用済みトークン (400) でエラーメッセージが表示される", async ({
    page,
  }) => {
    await page.route("**/api/families/join", (route) =>
      route.fulfill({
        status: 400,
        contentType: "application/json",
        body: JSON.stringify({ detail: "使用済み" }),
      })
    );

    await page.goto("/invite?token=expired-token");
    await expect(
      page.getByText("この招待は使用済みまたは期限切れです")
    ).toBeVisible();
  });

  test("email 不一致 (403 EMAIL_MISMATCH) でエラーメッセージが表示される", async ({
    page,
  }) => {
    await page.route("**/api/families/join", (route) =>
      route.fulfill({
        status: 403,
        contentType: "application/json",
        body: JSON.stringify({ detail: "EMAIL_MISMATCH" }),
      })
    );

    await page.goto("/invite?token=mismatch-token");
    await expect(
      page.getByText("招待先のメールアドレスとログイン中のアカウントが一致しません")
    ).toBeVisible();
  });
});

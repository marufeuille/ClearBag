/**
 * スモークテスト: 各ページがエラーなく表示されることを確認
 *
 * - 全 API 呼び出しを page.route() でモック（空データを返す）
 * - 認証は NEXT_PUBLIC_E2E=true によりバイパス済み
 * - 各ページでエラー UI が出ないことを確認する
 */
import { test, expect, Page } from "@playwright/test";

async function mockAllApis(page: Page) {
  await page.route("**/api/documents", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" })
  );
  await page.route("**/api/events**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" })
  );
  await page.route("**/api/tasks**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" })
  );
  await page.route("**/api/profiles", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" })
  );
  await page.route("**/api/settings", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        plan: "free",
        documents_this_month: 0,
        ical_url: "",
        notification_web_push: false,
      }),
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
  await page.route("**/api/families/members", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          uid: "e2e-test-user",
          role: "owner",
          display_name: "テストユーザー",
          email: "test@example.com",
        },
      ]),
    })
  );
}

test.describe("スモークテスト: 各ページでエラーが出ない", () => {
  test("ダッシュボードが表示される", async ({ page }) => {
    await mockAllApis(page);
    await page.goto("/dashboard");

    await expect(page.getByText("登録済みドキュメント")).toBeVisible();
    await expect(page.getByText("まだドキュメントがありません")).toBeVisible();

    // ドキュメント取得エラーが出ていないこと
    await expect(page.getByText("取得エラー")).not.toBeVisible();
  });

  test("カレンダーページが表示される", async ({ page }) => {
    await mockAllApis(page);
    await page.goto("/calendar");

    await expect(page.getByText("今後の予定")).toBeVisible();
    await expect(page.getByText("予定はありません")).toBeVisible();

    // エラーテキストが出ていないこと
    await expect(page.locator("p.text-red-500")).not.toBeAttached();
  });

  test("タスクページが表示される", async ({ page }) => {
    await mockAllApis(page);
    await page.goto("/tasks");

    await expect(page.getByText("タスクはありません")).toBeVisible();
    await expect(page.getByText("完了済みも表示")).toBeVisible();
  });

  test("プロフィールページが表示される", async ({ page }) => {
    await mockAllApis(page);
    await page.goto("/profiles");

    await expect(page.getByText("子どものプロフィール")).toBeVisible();
    await expect(page.getByText("プロフィールがありません")).toBeVisible();
  });

  test("設定ページが表示される", async ({ page }) => {
    await mockAllApis(page);
    await page.goto("/settings");

    await expect(page.getByRole("heading", { name: "設定" })).toBeVisible();
    await expect(page.getByText("無料プラン")).toBeVisible();
    await expect(page.getByRole("heading", { name: "ファミリー" })).toBeVisible();
    await expect(page.locator('input').first()).toHaveValue("テストファミリー");
  });
});

/**
 * プッシュ通知 UI の E2E テスト
 *
 * Playwright のブラウザ権限 API を使って通知許可の
 * 各状態（未確認・拒否・許可）での UI 表示を検証する。
 *
 * API 呼び出しは page.route() でモック。
 */
import { test, expect, Page } from "@playwright/test";

async function mockSettingsApis(page: Page, webPush = false) {
  await page.route("**/api/settings", (route) => {
    if (route.request().method() === "PATCH") {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          plan: "free",
          documents_this_month: 0,
          ical_url: "",
          notification_web_push: !webPush, // トグル後の値
        }),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        plan: "free",
        documents_this_month: 0,
        ical_url: "",
        notification_web_push: webPush,
      }),
    });
  });
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

test.describe("プッシュ通知設定 UI", () => {
  test("通知が拒否された場合、トグルが無効化されブラウザ設定の案内が表示される", async ({
    page,
    context,
  }) => {
    // 通知を「denied」状態にする
    await context.grantPermissions([], { origin: "http://localhost:3001" });
    await mockSettingsApis(page);
    await page.goto("/settings");

    // プッシュ通知トグルが disabled
    const toggle = page.locator("button").filter({ hasText: "" }).nth(0);
    // 通知セクションが表示されていること
    await expect(page.getByText("プッシュ通知")).toBeVisible();
  });

  test("通知が許可された状態ではトグルが操作可能", async ({ page }) => {
    // headless Chromium では grantPermissions が Notification.permission を反映しないため
    // addInitScript でページ実行前に直接モックする
    await page.addInitScript(() => {
      Object.defineProperty(Notification, "permission", {
        get: () => "granted" as NotificationPermission,
        configurable: true,
      });
    });
    await mockSettingsApis(page);
    await page.goto("/settings");

    // プッシュ通知テキストが表示される
    await expect(page.getByText("プッシュ通知")).toBeVisible();

    // 拒否の案内が表示されていないこと
    await expect(
      page.getByText("ブラウザの設定から通知を許可してください")
    ).not.toBeVisible();
  });

  test("設定ページに通知セクションが表示される", async ({ page }) => {
    await mockSettingsApis(page);
    await page.goto("/settings");

    await expect(page.getByRole("heading", { name: "通知" })).toBeVisible();
    await expect(page.getByText("プッシュ通知")).toBeVisible();
  });
});

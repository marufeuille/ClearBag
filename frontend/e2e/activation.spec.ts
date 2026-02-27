/**
 * アクティベーション状態チェックのテスト
 *
 * - /api/families/me が 403 ACTIVATION_REQUIRED → 「招待リンクが必要です」表示
 * - /api/families/me が 200 → 通常のダッシュボード表示
 */
import { test, expect, Page } from "@playwright/test";

async function mockApisForActivated(page: Page) {
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

test.describe("アクティベーション状態チェック", () => {
  test("未アクティベート時に「招待リンクが必要です」画面が表示される", async ({
    page,
  }) => {
    await page.route("**/api/families/me", (route) =>
      route.fulfill({
        status: 403,
        contentType: "application/json",
        body: JSON.stringify({ detail: "ACTIVATION_REQUIRED" }),
      })
    );

    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { name: "招待リンクが必要です" })).toBeVisible();
    await expect(
      page.getByText("既存ユーザーからの招待リンクが必要です")
    ).toBeVisible();
  });

  test("アクティベート済み時は通常のダッシュボードが表示される", async ({
    page,
  }) => {
    await mockApisForActivated(page);

    await page.goto("/dashboard");
    await expect(page.getByText("登録済みドキュメント")).toBeVisible();
    await expect(page.getByText("招待リンクが必要です")).not.toBeVisible();
  });

  test("その他の 403 エラーは通常ページとして表示される", async ({ page }) => {
    await page.route("**/api/families/me", (route) =>
      route.fulfill({
        status: 403,
        contentType: "application/json",
        body: JSON.stringify({ detail: "OTHER_ERROR" }),
      })
    );
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

    await page.goto("/dashboard");
    // ACTIVATION_REQUIRED 以外の 403 は通常ページとして扱う
    await expect(page.getByText("招待リンクが必要です")).not.toBeVisible();
    await expect(page.getByText("登録済みドキュメント")).toBeVisible();
  });
});

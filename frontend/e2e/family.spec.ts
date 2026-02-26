/**
 * 設定ページ: ファミリー管理セクションのテスト
 */
import { test, expect, Page } from "@playwright/test";

async function mockFamilyApis(
  page: Page,
  overrides?: { role?: "owner" | "member" }
) {
  const role = overrides?.role ?? "owner";

  await page.route("**/api/settings", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        plan: "free",
        documents_this_month: 0,
        ical_url: "",
        notification_email: false,
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
        role,
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
          display_name: "オーナーさん",
          email: "owner@example.com",
        },
        {
          uid: "member-uid-1",
          role: "member",
          display_name: "メンバーさん",
          email: "member@example.com",
        },
      ]),
    })
  );
}

test.describe("設定ページ: ファミリー管理", () => {
  test("オーナーはファミリー名・メンバー一覧・招待セクションを見られる", async ({
    page,
  }) => {
    await mockFamilyApis(page, { role: "owner" });
    await page.goto("/settings");

    await expect(page.getByRole("heading", { name: "ファミリー" })).toBeVisible();
    await expect(page.locator('input').first()).toHaveValue("テストファミリー");
    await expect(page.getByText("オーナーさん")).toBeVisible();
    await expect(page.getByText("メンバーさん")).toBeVisible();
    await expect(page.getByPlaceholder("メールアドレス")).toBeVisible();
  });

  test("オーナーはファミリー名を変更できる", async ({ page }) => {
    await mockFamilyApis(page, { role: "owner" });
    await page.route("**/api/families", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "family-1",
          name: "新しいファミリー名",
          plan: "free",
          documents_this_month: 0,
          role: "owner",
        }),
      })
    );
    await page.goto("/settings");

    const familyNameInput = page.locator('input').first();
    await expect(familyNameInput).toHaveValue("テストファミリー");
    await familyNameInput.fill("新しいファミリー名");
    await page.getByRole("button", { name: "保存" }).first().click();
    await expect(page.getByText("保存しました").first()).toBeVisible();
  });

  test("オーナーは招待URLを生成できる", async ({ page }) => {
    await mockFamilyApis(page, { role: "owner" });
    await page.route("**/api/families/invite", (route) =>
      route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          invitation_id: "inv-1",
          invite_url: "https://example.com/invite?token=abc",
        }),
      })
    );
    await page.goto("/settings");

    await page.getByPlaceholder("メールアドレス").fill("new@example.com");
    await page.getByRole("button", { name: "招待" }).click();
    await expect(
      page.locator('input[readonly]')
    ).toHaveValue("https://example.com/invite?token=abc");
  });

  test("オーナーはメンバーを削除できる", async ({ page }) => {
    await mockFamilyApis(page, { role: "owner" });
    await page.route("**/api/families/members/member-uid-1", (route) =>
      route.fulfill({ status: 204, body: "" })
    );
    await page.goto("/settings");

    page.on("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: "削除" }).click();
    await expect(page.getByText("メンバーさん")).not.toBeVisible();
  });

  test("メンバーロールでは招待・削除ボタンが表示されない", async ({ page }) => {
    await mockFamilyApis(page, { role: "member" });
    await page.goto("/settings");

    await expect(page.getByText("テストファミリー")).toBeVisible();
    await expect(page.getByPlaceholder("メールアドレス")).not.toBeVisible();
    await expect(page.getByRole("button", { name: "削除" })).not.toBeVisible();
  });
});

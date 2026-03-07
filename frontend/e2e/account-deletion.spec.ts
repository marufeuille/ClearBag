import { test, expect } from "@playwright/test";

test.describe("アカウント削除", () => {
  test("オーナー（1人のみ）: 削除ボタンが表示され、確認後に削除APIが呼ばれること", async ({
    page,
  }) => {
    // API モック: ファミリー情報（1人のみ）
    await page.route("**/api/families/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "fam-1",
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
          { uid: "owner-uid", role: "owner", display_name: "オーナー", email: "owner@test.com" },
        ]),
      })
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

    let deleteAccountCalled = false;
    await page.route("**/api/account", (route) => {
      if (route.request().method() === "DELETE") {
        deleteAccountCalled = true;
        route.fulfill({ status: 204 });
      }
    });

    await page.goto("/settings");

    // アカウント削除セクションが表示されていること
    await expect(page.getByText("アカウント削除")).toBeVisible();
    await expect(page.getByRole("button", { name: "アカウントを削除" })).toBeVisible();
    await expect(page.getByRole("button", { name: "アカウントを削除" })).toBeEnabled();
  });

  test("オーナー（他メンバーあり）: 削除ボタンが非表示で警告テキストが表示されること", async ({
    page,
  }) => {
    await page.route("**/api/families/me", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "fam-2",
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
          { uid: "owner-uid", role: "owner", display_name: "オーナー", email: "owner@test.com" },
          { uid: "member-uid", role: "member", display_name: "メンバー", email: "member@test.com" },
        ]),
      })
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

    await page.goto("/settings");

    // 削除ボタンが非表示で警告テキストが表示されること
    await expect(page.getByText("他のメンバーがいるため削除できません")).toBeVisible();
    await expect(page.getByRole("button", { name: "アカウントを削除" })).not.toBeVisible();
  });
});

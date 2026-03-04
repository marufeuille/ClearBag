/**
 * カレンダーページ E2E テスト
 *
 * - 月カレンダーグリッドのデフォルト表示
 * - 月ナビゲーション (◀▶)
 * - カレンダー/リスト切り替えトグル
 * - 日付タップ → リスト表示へ切り替わること
 * - ドット表示（予定あり日）
 * - 空状態表示
 */
import { test, expect, Page } from "@playwright/test";

const TODAY = new Date();
const YEAR = TODAY.getFullYear();
const MONTH = TODAY.getMonth(); // 0-indexed

function padTwo(n: number) {
  return String(n).padStart(2, "0");
}

/** 今月15日の日付文字列 (YYYY-MM-15) */
const EVENT_DATE = `${YEAR}-${padTwo(MONTH + 1)}-15`;

function mockEventApi(page: Page, hasEvents: boolean) {
  return page.route("**/api/events**", (route) => {
    if (!hasEvents) {
      return route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          summary: "遠足のお知らせ",
          start: `${EVENT_DATE}`,
          end: `${EVENT_DATE}`,
          location: "動物園",
          description: "",
          confidence: "HIGH",
        },
      ]),
    });
  });
}

async function mockCommonApis(page: Page) {
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
}

test.describe("カレンダーページ", () => {
  test("デフォルトでカレンダーグリッドが表示される", async ({ page }) => {
    await mockCommonApis(page);
    await mockEventApi(page, false);
    await page.goto("/calendar");

    // 曜日ヘッダー（日〜土）が表示されること
    for (const wd of ["日", "月", "火", "水", "木", "金", "土"]) {
      await expect(page.getByText(wd).first()).toBeVisible();
    }
  });

  test("現在の年月ラベルが表示される", async ({ page }) => {
    await mockCommonApis(page);
    await mockEventApi(page, false);
    await page.goto("/calendar");

    const label = `${YEAR}年${MONTH + 1}月`;
    await expect(page.getByText(label)).toBeVisible();
  });

  test("予定のある日にドットが表示される", async ({ page }) => {
    await mockCommonApis(page);
    await mockEventApi(page, true);
    await page.goto("/calendar");

    // 15日の日付ボタンが存在すること
    const dateButton = page.locator(`button[data-date="${EVENT_DATE}"]`);
    await expect(dateButton).toBeVisible();

    // ドット（bg-blue-400 クラスを持つ span）が visible であること
    const dot = dateButton.locator("span.bg-blue-400");
    await expect(dot).toBeVisible();
  });

  test("リストトグルでカードリスト表示に切り替わる", async ({ page }) => {
    await mockCommonApis(page);
    await mockEventApi(page, true);
    await page.goto("/calendar");

    // 初期状態: カレンダーグリッドが表示
    await expect(page.locator(`button[data-date="${EVENT_DATE}"]`)).toBeVisible();

    // リストボタンをクリック
    await page.getByRole("radio", { name: "リスト" }).click();

    // カードが表示されること
    await expect(page.getByText("遠足のお知らせ")).toBeVisible();
    // グリッドが非表示になること
    await expect(page.locator(`button[data-date="${EVENT_DATE}"]`)).not.toBeAttached();
  });

  test("カレンダートグルでグリッドに戻る", async ({ page }) => {
    await mockCommonApis(page);
    await mockEventApi(page, false);
    await page.goto("/calendar");

    // リストに切り替え
    await page.getByRole("radio", { name: "リスト" }).click();
    // カレンダーに戻す
    await page.getByRole("radio", { name: "カレンダー" }).click();

    // 曜日ヘッダーが再表示されること
    await expect(page.getByText("日").first()).toBeVisible();
  });

  test("◀ ボタンで前月に切り替わり月ラベルが変わる", async ({ page }) => {
    await mockCommonApis(page);
    await mockEventApi(page, false);
    await page.goto("/calendar");

    await page.getByRole("button", { name: "前の月" }).click();

    const prevMonth = MONTH === 0 ? 12 : MONTH;
    const prevYear = MONTH === 0 ? YEAR - 1 : YEAR;
    await expect(page.getByText(`${prevYear}年${prevMonth}月`)).toBeVisible();
  });

  test("▶ ボタンで次月に切り替わり月ラベルが変わる", async ({ page }) => {
    await mockCommonApis(page);
    await mockEventApi(page, false);
    await page.goto("/calendar");

    await page.getByRole("button", { name: "次の月" }).click();

    const nextMonth = MONTH === 11 ? 1 : MONTH + 2;
    const nextYear = MONTH === 11 ? YEAR + 1 : YEAR;
    await expect(page.getByText(`${nextYear}年${nextMonth}月`)).toBeVisible();
  });

  test("日付タップでリスト表示に切り替わる", async ({ page }) => {
    await mockCommonApis(page);
    await mockEventApi(page, true);
    await page.goto("/calendar");

    // カレンダー上の15日をタップ
    await page.locator(`button[data-date="${EVENT_DATE}"]`).click();

    // リスト表示に切り替わりイベントカードが表示されること
    await expect(page.getByText("遠足のお知らせ")).toBeVisible();
    // カレンダーグリッドが消えること
    await expect(page.locator(`button[data-date="${EVENT_DATE}"]`)).not.toBeAttached();
  });

  test("予定0件で「予定はありません」が表示される", async ({ page }) => {
    await mockCommonApis(page);
    await mockEventApi(page, false);
    await page.goto("/calendar");

    await expect(page.getByText("予定はありません")).toBeVisible();
  });
});

/**
 * アクティベーション状態の localStorage キャッシュ
 *
 * アクティベーション確認済みの結果を TTL 付きでキャッシュし、
 * 2回目以降の訪問で API 呼び出し（と Cold Start）をスキップできるようにする。
 * "activated" の状態のみキャッシュし、未アクティベートはキャッシュしない。
 */

const TTL_MS = 24 * 60 * 60 * 1000; // 24時間

function cacheKey(uid: string) {
  return `clearbag_activated_${uid}`;
}

/** キャッシュに有効なアクティベーション済み記録があれば true、なければ null */
export function loadActivationCache(uid: string): true | null {
  try {
    const raw = localStorage.getItem(cacheKey(uid));
    if (!raw) return null;
    const { ts } = JSON.parse(raw) as { ts: number };
    if (Date.now() - ts > TTL_MS) {
      localStorage.removeItem(cacheKey(uid));
      return null;
    }
    return true;
  } catch {
    return null;
  }
}

/** アクティベーション済みをキャッシュに保存 */
export function saveActivationCache(uid: string) {
  try {
    localStorage.setItem(cacheKey(uid), JSON.stringify({ ts: Date.now() }));
  } catch {
    // localStorage が使えない環境（プライベートブラウジング等）は無視
  }
}

/** キャッシュを削除（メンバー除外時などに呼ぶ） */
export function clearActivationCache(uid: string) {
  try {
    localStorage.removeItem(cacheKey(uid));
  } catch {}
}

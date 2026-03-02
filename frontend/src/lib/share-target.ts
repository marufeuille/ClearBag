/**
 * Web Share Target API 定数
 *
 * Service Worker（worker/index.ts）とページ側（useShareTarget hook）で
 * Cache API のキー名を共有するための定数。
 *
 * NOTE: worker/index.ts は tsconfig の exclude にあるため import 不可。
 * SW 側ではこれらの値をリテラルで直書きしている。
 */

export const SHARE_TARGET_CACHE_NAME = "clearbag-share-target";
export const SHARE_TARGET_CACHE_KEY = "/share-target-file";

/** キャッシュの有効期限（ミリ秒）: 5分 */
export const SHARE_TARGET_TTL_MS = 5 * 60 * 1000;

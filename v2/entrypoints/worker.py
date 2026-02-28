"""Cloud Tasks ワーカー エントリーポイント

Cloud Tasks から HTTP POST を受け取り、ドキュメント解析を非同期実行する。

受け取るペイロード（JSON）:
  {
    "uid": "firebase-auth-uid",
    "family_id": "family-uuid",
    "document_id": "uuid",
    "storage_path": "uploads/{family_id}/{document_id}.pdf",
    "mime_type": "application/pdf"
  }

処理フロー:
  1. GCS からファイルをダウンロード
  2. Firestore からファミリーのプロファイルを取得
  3. DocumentProcessor で AI 解析
  4. 解析結果を Firestore に保存（families/{family_id} 配下）
  5. WebPush 通知（設定済みの場合）
"""

from __future__ import annotations

import logging
import os

import firebase_admin
import vertexai
from fastapi import APIRouter, Depends, HTTPException, Request, status
from firebase_admin import credentials as fb_creds
from google.cloud import firestore
from vertexai.generative_models import GenerativeModel

from v2.adapters.cloud_storage import GCSBlobStorage
from v2.adapters.firestore_repository import (
    FirestoreDocumentRepository,
    FirestoreFamilyRepository,
    FirestoreUserConfigRepository,
)
from v2.adapters.gemini import GeminiDocumentAnalyzer
from v2.domain.models import Profile, UserProfile
from v2.entrypoints.api.worker_auth import verify_worker_token
from v2.services.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)

# ── 初期化（プロセス起動時に1回のみ実行） ────────────────────────────────────


def _ensure_firebase_init() -> None:
    """Firebase Admin を初期化する（二重初期化を防ぐ）"""
    try:
        firebase_admin.get_app()
    except ValueError:
        cred = fb_creds.ApplicationDefault()
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin initialized (worker)")


def _build_processor() -> DocumentProcessor:
    """DocumentProcessor を組み立てる"""
    project_id = os.environ["PROJECT_ID"]
    location = os.environ.get("VERTEX_AI_LOCATION", "us-central1")
    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")

    vertexai.init(project=project_id, location=location)
    model = GenerativeModel(model_name)
    analyzer = GeminiDocumentAnalyzer(model=model)
    return DocumentProcessor(analyzer=analyzer)


def run_analysis_sync(
    uid: str,
    family_id: str,
    document_id: str,
    storage_path: str,
    mime_type: str,
) -> None:
    """
    ドキュメント解析のコアロジック。

    Cloud Tasks HTTP ハンドラーとローカル開発の BackgroundTasks の両方から
    呼び出される共通実装。

    Args:
        uid: アップロードした個人の Firebase Auth UID（通知送信に使用）
        family_id: ファミリー ID（プロファイル取得・解析結果保存に使用）
        document_id: ドキュメント ID
        storage_path: GCS 上のファイルパス
        mime_type: MIME タイプ
    """
    _ensure_firebase_init()
    logger.info(
        "Analysis started: family_id=%s, uid=%s, doc_id=%s",
        family_id,
        uid,
        document_id,
    )

    db = firestore.Client()
    doc_repo = FirestoreDocumentRepository(db)
    family_repo = FirestoreFamilyRepository(db)
    user_repo = FirestoreUserConfigRepository(db)
    blob_storage = GCSBlobStorage(bucket_name=os.environ["GCS_BUCKET_NAME"])

    try:
        doc_repo.update_status(family_id, document_id, "processing")

        content = blob_storage.download(storage_path)
        logger.info("Downloaded: path=%s, size=%d bytes", storage_path, len(content))

        # ファミリーのプロファイルを取得して Gemini に渡す
        user_profiles = family_repo.list_profiles(family_id)
        profiles = _convert_profiles(user_profiles)

        processor = _build_processor()
        analysis = processor.process(content, mime_type, profiles, rules=[])

        doc_repo.save_analysis(family_id, document_id, analysis)
        logger.info(
            "Analysis saved: family_id=%s, doc_id=%s, category=%s",
            family_id,
            document_id,
            analysis.category.value,
        )

        # 通知はアップロードした個人の設定に従って送信
        _try_send_notification(uid, family_id, document_id, analysis, user_repo, db)

    except Exception as e:
        logger.exception(
            "Worker failed: family_id=%s, doc_id=%s", family_id, document_id
        )
        doc_repo.update_status(family_id, document_id, "error", error_message=str(e))
        raise


# ── Worker ルーター（app.py で /worker プレフィックスにマウント） ───────────────

router = APIRouter(dependencies=[Depends(verify_worker_token)])


@router.post("/analyze", status_code=status.HTTP_200_OK)
async def analyze_document(request: Request) -> dict:
    """
    Cloud Tasks から呼び出されるドキュメント解析エンドポイント。

    OIDC トークン検証は verify_worker_token Depends によりアプリレベルで実施済み。
    """
    payload = await request.json()
    uid: str = payload["uid"]
    family_id: str = payload["family_id"]
    document_id: str = payload["document_id"]
    storage_path: str = payload["storage_path"]
    mime_type: str = payload["mime_type"]

    try:
        run_analysis_sync(uid, family_id, document_id, storage_path, mime_type)
        return {"status": "completed", "document_id": document_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {e}",
        ) from e


def _convert_profiles(user_profiles: list[UserProfile]) -> dict[str, Profile]:
    """
    UserProfile（B2C）を Profile（既存 Gemini アナライザー用）に変換。

    B2C では calendar_id は不要なので空文字列を設定する。
    """
    return {
        p.id: Profile(
            id=p.id,
            name=p.name,
            grade=p.grade,
            keywords=p.keywords,
            calendar_id="",  # B2C では不使用
        )
        for p in user_profiles
    }


@router.post("/morning-digest", status_code=status.HTTP_200_OK)
async def morning_digest(request: Request) -> dict:
    """
    朝のダイジェスト WebPush 送信エンドポイント（Cloud Scheduler から呼び出し）。

    web_push 通知を有効化した全ユーザーに今後7日間の予定・未完了タスク件数をプッシュ通知する。
    Cloud Scheduler の OIDC トークンで保護される想定。
    """
    _ensure_firebase_init()

    vapid_private_key = os.environ.get("VAPID_PRIVATE_KEY", "")
    if not vapid_private_key:
        logger.warning("VAPID_PRIVATE_KEY not set, skipping morning digest")
        return {"status": "skipped", "reason": "no_vapid_key"}

    import datetime

    from google.cloud.firestore import DELETE_FIELD

    from v2.adapters.webpush_notifier import (
        PushSubscription,
        VapidConfig,
        WebPushNotifier,
    )

    vapid_public_key = os.environ.get("VAPID_PUBLIC_KEY", "")
    vapid_email = os.environ.get("VAPID_CLAIMS_EMAIL", "")
    notifier = WebPushNotifier(
        VapidConfig(
            private_key=vapid_private_key,
            public_key=vapid_public_key,
            claims_email=vapid_email,
        )
    )

    db = firestore.Client()
    doc_repo = FirestoreDocumentRepository(db)

    today = datetime.date.today()
    from_date = today.isoformat()
    to_date = (today + datetime.timedelta(days=7)).isoformat()

    sent = 0
    errors = 0

    users_ref = db.collection("users").stream()
    for user_doc in users_ref:
        uid = user_doc.id
        user_data = user_doc.to_dict() or {}
        prefs = user_data.get("notification_preferences", {})
        family_id = user_data.get("family_id")

        if not prefs.get("web_push", False) or not family_id:
            continue

        all_subs = _collect_subscriptions(user_data)
        if not all_subs:
            continue

        try:
            events = doc_repo.list_events(
                family_id, from_date=from_date, to_date=to_date
            )
            tasks = doc_repo.list_tasks(family_id, completed=False)
        except Exception:
            logger.exception("Morning digest data fetch failed for uid=%s", uid)
            errors += 1
            continue

        for field_key, subscription_data in all_subs:
            try:
                sub = PushSubscription(
                    endpoint=subscription_data["endpoint"],
                    keys=subscription_data["keys"],
                )
                notifier.notify_morning_digest(sub, len(events), len(tasks))
                sent += 1
            except Exception as e:
                # 410 Gone はサブスクリプション失効 → 該当端末のみ削除
                if _is_gone_error(e):
                    logger.info(
                        "Push subscription expired, removing: uid=%s, field=%s",
                        uid,
                        field_key,
                    )
                    db.collection("users").document(uid).update(
                        {field_key: DELETE_FIELD}
                    )
                else:
                    logger.exception("Morning digest failed for uid=%s", uid)
                errors += 1

    logger.info("Morning digest complete: sent=%d, errors=%d", sent, errors)
    return {"status": "ok", "sent": sent, "errors": errors}


@router.post("/event-reminder", status_code=status.HTTP_200_OK)
async def event_reminder(request: Request) -> dict:
    """
    翌日イベントリマインダー WebPush 送信エンドポイント（Cloud Scheduler から呼び出し）。

    翌日に予定があるユーザーに対してプッシュ通知を送信する。
    Cloud Scheduler の OIDC トークンで保護される想定。
    """
    _ensure_firebase_init()

    vapid_private_key = os.environ.get("VAPID_PRIVATE_KEY", "")
    if not vapid_private_key:
        logger.warning("VAPID_PRIVATE_KEY not set, skipping event reminder")
        return {"status": "skipped", "reason": "no_vapid_key"}

    import datetime

    from google.cloud.firestore import DELETE_FIELD

    from v2.adapters.webpush_notifier import (
        PushSubscription,
        VapidConfig,
        WebPushNotifier,
    )

    vapid_public_key = os.environ.get("VAPID_PUBLIC_KEY", "")
    vapid_email = os.environ.get("VAPID_CLAIMS_EMAIL", "")
    notifier = WebPushNotifier(
        VapidConfig(
            private_key=vapid_private_key,
            public_key=vapid_public_key,
            claims_email=vapid_email,
        )
    )

    db = firestore.Client()
    doc_repo = FirestoreDocumentRepository(db)

    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

    sent = 0
    errors = 0

    users_ref = db.collection("users").stream()
    for user_doc in users_ref:
        uid = user_doc.id
        user_data = user_doc.to_dict() or {}
        prefs = user_data.get("notification_preferences", {})
        family_id = user_data.get("family_id")

        if not prefs.get("web_push", False) or not family_id:
            continue

        all_subs = _collect_subscriptions(user_data)
        if not all_subs:
            continue

        try:
            events = doc_repo.list_events(
                family_id, from_date=tomorrow, to_date=tomorrow
            )
        except Exception:
            logger.exception("Event reminder data fetch failed for uid=%s", uid)
            errors += 1
            continue

        if not events:
            continue

        for field_key, subscription_data in all_subs:
            try:
                sub = PushSubscription(
                    endpoint=subscription_data["endpoint"],
                    keys=subscription_data["keys"],
                )
                notifier.notify_event_reminder(sub, events)
                sent += 1
            except Exception as e:
                if _is_gone_error(e):
                    logger.info(
                        "Push subscription expired, removing: uid=%s, field=%s",
                        uid,
                        field_key,
                    )
                    db.collection("users").document(uid).update(
                        {field_key: DELETE_FIELD}
                    )
                else:
                    logger.exception("Event reminder failed for uid=%s", uid)
                errors += 1

    logger.info("Event reminder complete: sent=%d, errors=%d", sent, errors)
    return {"status": "ok", "sent": sent, "errors": errors}


def _is_gone_error(e: Exception) -> bool:
    """WebPushException の HTTP 410 Gone を判定する"""
    from pywebpush import WebPushException

    return (
        isinstance(e, WebPushException)
        and getattr(e, "response", None) is not None
        and e.response.status_code == 410
    )


def _collect_subscriptions(user_data: dict) -> list[tuple[str, dict]]:
    """
    ユーザーデータから全サブスクリプションを返す。

    新形式 (web_push_subscriptions map) と旧形式 (web_push_subscription 単数)
    の両方をサポートする（移行期間の後方互換）。

    Returns:
        [(firestore_field_key, subscription_data), ...]
    """
    result: list[tuple[str, dict]] = []
    subscriptions_map = user_data.get("web_push_subscriptions") or {}
    for key, sub_data in subscriptions_map.items():
        result.append((f"web_push_subscriptions.{key}", sub_data))
    # 旧形式: 移行期間の後方互換
    old_sub = user_data.get("web_push_subscription")
    if old_sub:
        result.append(("web_push_subscription", old_sub))
    return result


def _try_send_notification(
    uid: str,
    family_id: str,
    document_id: str,
    analysis,
    user_repo: FirestoreUserConfigRepository,
    db: firestore.Client,
) -> None:
    """
    通知設定に基づいて全端末の WebPush 通知を試みる。
    通知の失敗は無視してメインフローを継続する。
    通知設定は個人単位（uid）で管理する。
    """
    try:
        user = user_repo.get_user(uid)
        prefs = user.get("notification_preferences", {})

        if not prefs.get("web_push", False):
            return

        all_subs = _collect_subscriptions(user)
        vapid_private_key = os.environ.get("VAPID_PRIVATE_KEY", "")
        vapid_public_key = os.environ.get("VAPID_PUBLIC_KEY", "")
        vapid_email = os.environ.get("VAPID_CLAIMS_EMAIL", "")

        if not all_subs or not vapid_private_key:
            return

        from v2.adapters.webpush_notifier import (
            PushSubscription,
            VapidConfig,
            WebPushNotifier,
        )

        notifier_wp = WebPushNotifier(
            VapidConfig(
                private_key=vapid_private_key,
                public_key=vapid_public_key,
                claims_email=vapid_email,
            )
        )
        doc_snap = (
            db.collection("families")
            .document(family_id)
            .collection("documents")
            .document(document_id)
            .get()
        )
        original_filename = (
            doc_snap.get("original_filename") if doc_snap.exists else "document"
        )

        for field_key, subscription_data in all_subs:
            sub = PushSubscription(
                endpoint=subscription_data["endpoint"],
                keys=subscription_data["keys"],
            )
            try:
                notifier_wp.notify_analysis_complete(
                    sub, original_filename, document_id
                )
            except Exception as e:
                if _is_gone_error(e):
                    from google.cloud.firestore import DELETE_FIELD

                    logger.info(
                        "Push subscription expired, removing: uid=%s, field=%s",
                        uid,
                        field_key,
                    )
                    db.collection("users").document(uid).update(
                        {field_key: DELETE_FIELD}
                    )
                else:
                    raise

    except Exception:
        logger.exception(
            "Notification failed (non-critical): uid=%s, doc_id=%s", uid, document_id
        )

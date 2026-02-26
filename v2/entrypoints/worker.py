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
  5. メール/WebPush 通知（設定済みの場合）
"""

from __future__ import annotations

import logging
import os

import firebase_admin
import vertexai
from fastapi import APIRouter, HTTPException, Request, status
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

router = APIRouter()


@router.post("/analyze", status_code=status.HTTP_200_OK)
async def analyze_document(request: Request) -> dict:
    """
    Cloud Tasks から呼び出されるドキュメント解析エンドポイント。

    Cloud Tasks の OIDC トークン検証は Cloud Run のオーディエンス設定で行う。
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
    朝のダイジェストメール送信エンドポイント（Cloud Scheduler から呼び出し）。

    全ファミリーメンバーに対して今後7日間の予定・未完了タスクをメールで送信する。
    Cloud Scheduler の OIDC トークンで保護される想定。
    """
    _ensure_firebase_init()

    db = firestore.Client()
    doc_repo = FirestoreDocumentRepository(db)

    sendgrid_key = os.environ.get("SENDGRID_API_KEY", "")
    if not sendgrid_key:
        logger.warning("SENDGRID_API_KEY not set, skipping morning digest")
        return {"status": "skipped", "reason": "no_sendgrid_key"}

    from v2.adapters.email_notifier import EmailConfig, SendGridEmailNotifier

    notifier = SendGridEmailNotifier(EmailConfig(api_key=sendgrid_key))

    import datetime

    today = datetime.date.today()
    from_date = today.isoformat()
    to_date = (today + datetime.timedelta(days=7)).isoformat()

    sent = 0
    errors = 0

    # 全ユーザーを走査し、family_id からファミリーのイベント/タスクを取得
    users_ref = db.collection("users").stream()
    for user_doc in users_ref:
        uid = user_doc.id
        user_data = user_doc.to_dict() or {}
        prefs = user_data.get("notification_preferences", {})
        user_email = user_data.get("email", "")
        family_id = user_data.get("family_id")

        if not prefs.get("email", False) or not user_email or not family_id:
            continue

        try:
            # ファミリー単位でイベント/タスクを取得
            events = doc_repo.list_events(
                family_id, from_date=from_date, to_date=to_date
            )
            tasks = doc_repo.list_tasks(family_id, completed=False)
            notifier.send_morning_digest(
                to_email=user_email,
                upcoming_events=events,
                pending_tasks=tasks,
            )
            sent += 1
        except Exception:
            logger.exception("Morning digest failed for uid=%s", uid)
            errors += 1

    logger.info("Morning digest complete: sent=%d, errors=%d", sent, errors)
    return {"status": "ok", "sent": sent, "errors": errors}


def _try_send_notification(
    uid: str,
    family_id: str,
    document_id: str,
    analysis,
    user_repo: FirestoreUserConfigRepository,
    db: firestore.Client,
) -> None:
    """
    通知設定に基づいてメール/WebPush 通知を試みる。
    通知の失敗は無視してメインフローを継続する。
    通知設定は個人単位（uid）で管理する。
    """
    try:
        user = user_repo.get_user(uid)
        prefs = user.get("notification_preferences", {})

        # メール通知
        sendgrid_key = os.environ.get("SENDGRID_API_KEY", "")
        user_email = user.get("email", "")
        if prefs.get("email", False) and sendgrid_key and user_email:
            from v2.adapters.email_notifier import EmailConfig, SendGridEmailNotifier

            notifier = SendGridEmailNotifier(EmailConfig(api_key=sendgrid_key))
            # families/{family_id}/documents/{document_id} からファイル名を取得
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
            notifier.notify_analysis_complete(
                to_email=user_email,
                original_filename=original_filename,
                summary=analysis.summary,
                events=analysis.events,
                tasks=analysis.tasks,
            )

        # Web Push 通知
        if prefs.get("web_push", False):
            subscription_data = user.get("web_push_subscription")
            vapid_private_key = os.environ.get("VAPID_PRIVATE_KEY", "")
            vapid_public_key = os.environ.get("VAPID_PUBLIC_KEY", "")
            vapid_email = os.environ.get("VAPID_CLAIMS_EMAIL", "")

            if subscription_data and vapid_private_key:
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
                sub = PushSubscription(
                    endpoint=subscription_data["endpoint"],
                    keys=subscription_data["keys"],
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
                notifier_wp.notify_analysis_complete(
                    sub, original_filename, document_id
                )

    except Exception:
        logger.exception(
            "Notification failed (non-critical): uid=%s, doc_id=%s", uid, document_id
        )

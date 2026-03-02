"""Worker エンドポイント用 OIDC トークン検証

Cloud Tasks / Cloud Scheduler が付与する Google OIDC トークンを検証し、
想定外の呼び出し元からのリクエストを 401 で拒否する。

検証方針:
- audience は検証しない（Cloud Tasks と Cloud Scheduler で値が異なるため）
- email claim が WORKER_SERVICE_ACCOUNT_EMAIL と一致することで呼び出し元を確認
- WORKER_SERVICE_ACCOUNT_EMAIL 未設定時は fail-closed（401 を返す）
- LOCAL_MODE=true 時は検証をスキップ（BackgroundTasks 経由で直接呼ばれるため）
"""

from __future__ import annotations

import logging
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

logger = logging.getLogger(__name__)

# auto_error=False にすることで、Bearer ヘッダーがない場合に 403 ではなく
# 自前の 401 を返せるようにする
_bearer_scheme = HTTPBearer(auto_error=False)


def verify_worker_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> None:
    """
    Worker エンドポイントの OIDC トークン検証 Depends 関数。

    FastAPI の Depends() に渡して /worker/* ルーターに適用する。
    検証に失敗した場合は 401 Unauthorized を raise する。
    """
    # LOCAL_MODE では Cloud Tasks を使わず BackgroundTasks 経由で直接呼ぶため検証不要
    if os.environ.get("LOCAL_MODE"):
        return

    expected_email = os.environ.get("WORKER_SERVICE_ACCOUNT_EMAIL")
    if not expected_email:
        # 環境変数未設定は設定ミスとみなし fail-closed
        logger.error("WORKER_SERVICE_ACCOUNT_EMAIL is not set; denying worker request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Worker authentication is not configured",
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    token = credentials.credentials
    try:
        # audience=None: Cloud Tasks と Cloud Scheduler で audience が異なるため検証しない
        id_info = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            audience=None,
        )
    except Exception as exc:
        logger.warning("OIDC token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OIDC token",
        ) from exc

    actual_email = id_info.get("email", "")
    if actual_email != expected_email:
        logger.warning(
            "OIDC email mismatch: expected=%s, got=%s", expected_email, actual_email
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized service account",
        )

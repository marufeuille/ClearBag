"""ensure_monthly_reset のユニットテスト

月間利用枚数カウンターのリセット処理（Lazy Reset）を検証する。
"""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock

from v2.entrypoints.api.usage import ensure_monthly_reset


def _dt(year: int, month: int, day: int = 1) -> datetime.datetime:
    """テスト用の UTC datetime を生成するヘルパー"""
    return datetime.datetime(year, month, day, tzinfo=datetime.UTC)


class TestEnsureMonthlyReset:
    """ensure_monthly_reset の各シナリオをテスト"""

    def test_same_month_no_reset(self):
        """同月内アクセス: リセットしない"""
        # Arrange
        repo = MagicMock()
        family = {"documents_this_month": 3, "last_reset_at": _dt(2026, 2, 1)}
        now = _dt(2026, 2, 15)

        # Act
        result = ensure_monthly_reset(repo, "fam1", family, _now=now)

        # Assert
        repo.update_family.assert_not_called()
        assert result["documents_this_month"] == 3

    def test_month_changed_resets_counter(self):
        """月変わり（1月→2月）: カウンター 0 にリセット"""
        # Arrange
        repo = MagicMock()
        family = {"documents_this_month": 5, "last_reset_at": _dt(2026, 1, 1)}
        now = _dt(2026, 2, 1)

        # Act
        result = ensure_monthly_reset(repo, "fam1", family, _now=now)

        # Assert
        repo.update_family.assert_called_once_with(
            "fam1", {"documents_this_month": 0, "last_reset_at": now}
        )
        assert result["documents_this_month"] == 0

    def test_year_changed_resets_counter(self):
        """年またぎ（12月→1月）: カウンター 0 にリセット"""
        # Arrange
        repo = MagicMock()
        family = {"documents_this_month": 4, "last_reset_at": _dt(2025, 12, 1)}
        now = _dt(2026, 1, 1)

        # Act
        result = ensure_monthly_reset(repo, "fam1", family, _now=now)

        # Assert
        repo.update_family.assert_called_once_with(
            "fam1", {"documents_this_month": 0, "last_reset_at": now}
        )
        assert result["documents_this_month"] == 0

    def test_last_reset_at_none_initializes_without_reset(self):
        """last_reset_at が None: 初期化のみ、カウントはリセットしない"""
        # Arrange
        repo = MagicMock()
        family = {"documents_this_month": 3, "last_reset_at": None}
        now = _dt(2026, 2, 1)

        # Act
        result = ensure_monthly_reset(repo, "fam1", family, _now=now)

        # Assert
        repo.update_family.assert_called_once_with("fam1", {"last_reset_at": now})
        assert result["documents_this_month"] == 3

    def test_last_reset_at_key_missing_initializes_without_reset(self):
        """last_reset_at キー未存在: last_reset_at=None と同じ挙動"""
        # Arrange
        repo = MagicMock()
        family = {"documents_this_month": 2}  # last_reset_at キー自体がない
        now = _dt(2026, 2, 1)

        # Act
        result = ensure_monthly_reset(repo, "fam1", family, _now=now)

        # Assert
        repo.update_family.assert_called_once_with("fam1", {"last_reset_at": now})
        assert result["documents_this_month"] == 2

    def test_return_value_contains_updated_fields(self):
        """戻り値の正しさ: リセット後 dict に更新後の値が含まれ、既存フィールドは保持される"""
        # Arrange
        repo = MagicMock()
        family = {
            "plan": "free",
            "name": "テストファミリー",
            "documents_this_month": 5,
            "last_reset_at": _dt(2026, 1, 1),
        }
        now = _dt(2026, 2, 1)

        # Act
        result = ensure_monthly_reset(repo, "fam1", family, _now=now)

        # Assert
        assert result["documents_this_month"] == 0
        assert result["last_reset_at"] == now
        assert result["plan"] == "free"  # 既存フィールドが保持される
        assert result["name"] == "テストファミリー"  # 既存フィールドが保持される

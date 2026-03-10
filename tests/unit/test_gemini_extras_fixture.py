"""Gemini extras 抽出のFixture再生テスト

## 目的
Gemini APIを呼ばずに、保存済みレスポンスJSON（tests/fixtures/gemini_responses/）を
使って _convert_to_domain_model() の変換・extras抽出ロジックを検証する。

## テスト構造
- 通常テスト: fixtures/ の JSON を読み込んで変換を検証。CI で常時実行。
- 録画テスト (@pytest.mark.manual): 実 Gemini API を呼び出してレスポンスを
  fixtures/ に保存する。Gemini モデル更新時や新しいPDFパターン追加時に手動実行。

## 録画手順（新しいPDFパターンを追加するとき）
    PROJECT_ID=clearbag-dev uv run pytest tests/unit/test_gemini_extras_fixture.py \
        -m manual -v -s \
        --pdf-path=/path/to/sample.pdf \
        --fixture-name=my_new_fixture

## Fixture フォーマット
- gemini_responses/{name}.json : Gemini が返す生 JSON（output schema 準拠）
- expectations/{name}.json    : 期待値の宣言（set-containment 形式）
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from v2.adapters.gemini import GeminiDocumentAnalyzer
from v2.domain.models import DocumentExtras

# ── フィクスチャパス ──────────────────────────────────────────────────────────

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
_RESPONSES_DIR = _FIXTURES_DIR / "gemini_responses"
_EXPECTATIONS_DIR = _FIXTURES_DIR / "expectations"

# テスト対象のフィクスチャ名（gemini_responses/ と expectations/ の両方に同名ファイルがある）
_FIXTURE_NAMES = [
    "excursion_notice",  # 遠足：持ち物・服装・費用・注意事項
    "cost_notice",       # 集金：複数費用
    "schedule_only",     # 行事予定のみ：extras なし
]


# ── ヘルパー：期待値チェック ──────────────────────────────────────────────────


def _item_names(extras: DocumentExtras | None) -> list[str]:
    if not extras:
        return []
    return [i.item for i in extras.items_to_bring]


def _dress_code_str(extras: DocumentExtras | None) -> list[str]:
    return extras.dress_code if extras else []


def _note_str(extras: DocumentExtras | None) -> list[str]:
    return extras.notes if extras else []


def _assert_extras_meets_expectations(
    extras: DocumentExtras | None,
    expectation: dict | None,
    fixture_name: str,
) -> None:
    """extras が expectations の宣言を満たしているか検証する。

    expectations.json の "extras" が null の場合は extras が None または空であることを確認。
    そうでない場合は must_contain_* による set-containment チェックを行う。
    """
    if expectation is None:
        # extrasなしが期待される（空のDocumentExtrasも許容）
        if extras is not None:
            # 全フィールドが空ならOK（Geminiが空配列で返してくる場合）
            assert not _item_names(extras), f"[{fixture_name}] extras.items_to_bring は空であるべき"
            assert not _dress_code_str(extras), f"[{fixture_name}] extras.dress_code は空であるべき"
            assert not extras.costs, f"[{fixture_name}] extras.costs は空であるべき"
            assert not _note_str(extras), f"[{fixture_name}] extras.notes は空であるべき"
        return

    actual_items = _item_names(extras)
    actual_dress = _dress_code_str(extras)
    actual_notes = _note_str(extras)

    # 持ち物チェック（完全一致）
    for expected_item in expectation.get("must_contain_items", []):
        assert expected_item in actual_items, (
            f"[{fixture_name}] 持ち物 '{expected_item}' が見つからない。実際: {actual_items}"
        )

    # 服装チェック（部分一致）
    for keyword in expectation.get("must_contain_dress_code_keywords", []):
        matched = any(keyword in d for d in actual_dress)
        assert matched, (
            f"[{fixture_name}] 服装キーワード '{keyword}' が見つからない。実際: {actual_dress}"
        )

    # 費用チェック
    actual_costs = extras.costs if extras else []
    for cost_exp in expectation.get("costs", []):
        desc_keyword = cost_exp["description_contains"]
        matched_cost = next(
            (c for c in actual_costs if desc_keyword in c.description), None
        )
        assert matched_cost is not None, (
            f"[{fixture_name}] 費用 '{desc_keyword}' が見つからない。"
            f"実際: {[c.description for c in actual_costs]}"
        )
        if "amount_range" in cost_exp and matched_cost.amount is not None:
            lo, hi = cost_exp["amount_range"]
            assert lo <= matched_cost.amount <= hi, (
                f"[{fixture_name}] 費用 '{desc_keyword}' の金額 {matched_cost.amount} が"
                f" 範囲 [{lo}, {hi}] 外"
            )
        if "due_date_prefix" in cost_exp and matched_cost.due_date:
            prefix = cost_exp["due_date_prefix"]
            assert matched_cost.due_date.startswith(prefix), (
                f"[{fixture_name}] 費用 '{desc_keyword}' の期限 '{matched_cost.due_date}' が"
                f" '{prefix}' で始まらない"
            )

    # 注意事項チェック（部分一致）
    for keyword in expectation.get("must_contain_note_keywords", []):
        matched = any(keyword in note for note in actual_notes)
        assert matched, (
            f"[{fixture_name}] 注意事項キーワード '{keyword}' が見つからない。実際: {actual_notes}"
        )


# ── 通常テスト（CI で常時実行）────────────────────────────────────────────────


class TestGeminiExtrasFixture:
    """保存済みGeminiレスポンスからextrasが正しく変換されることを検証する。

    tests/fixtures/gemini_responses/*.json を入力として _convert_to_domain_model() を呼び出し、
    tests/fixtures/expectations/*.json の宣言と照合する。
    """

    # GeminiDocumentAnalyzerは model=None でもパーサーメソッドは使える
    _analyzer = GeminiDocumentAnalyzer.__new__(GeminiDocumentAnalyzer)

    @pytest.mark.parametrize("fixture_name", _FIXTURE_NAMES)
    def test_extras_conversion_from_fixture(self, fixture_name: str) -> None:
        """フィクスチャJSONを変換し、期待値を満たすことを確認する"""
        response_path = _RESPONSES_DIR / f"{fixture_name}.json"
        expectation_path = _EXPECTATIONS_DIR / f"{fixture_name}.json"

        assert response_path.exists(), f"フィクスチャファイルが存在しない: {response_path}"
        assert expectation_path.exists(), f"期待値ファイルが存在しない: {expectation_path}"

        raw_json = json.loads(response_path.read_text(encoding="utf-8"))
        expectation_json = json.loads(expectation_path.read_text(encoding="utf-8"))

        analysis = self._analyzer._convert_to_domain_model(raw_json)

        _assert_extras_meets_expectations(
            extras=analysis.extras,
            expectation=expectation_json.get("extras"),
            fixture_name=fixture_name,
        )

    @pytest.mark.parametrize("fixture_name", _FIXTURE_NAMES)
    def test_extras_event_index_in_bounds(self, fixture_name: str) -> None:
        """items_to_bring の event_index が events リストの範囲内か、または -1 であること"""
        raw_json = json.loads(
            (_RESPONSES_DIR / f"{fixture_name}.json").read_text(encoding="utf-8")
        )
        analysis = self._analyzer._convert_to_domain_model(raw_json)

        if analysis.extras is None:
            return

        num_events = len(analysis.events)
        for item in analysis.extras.items_to_bring:
            assert item.event_index == -1 or 0 <= item.event_index < num_events, (
                f"[{fixture_name}] '{item.item}' の event_index={item.event_index} が"
                f" 範囲外 (events: {num_events}件)"
            )

    @pytest.mark.parametrize("fixture_name", _FIXTURE_NAMES)
    def test_extras_cost_amount_non_negative(self, fixture_name: str) -> None:
        """costs の amount は None か非負の整数であること"""
        raw_json = json.loads(
            (_RESPONSES_DIR / f"{fixture_name}.json").read_text(encoding="utf-8")
        )
        analysis = self._analyzer._convert_to_domain_model(raw_json)

        if analysis.extras is None:
            return

        for cost in analysis.extras.costs:
            if cost.amount is not None:
                assert cost.amount >= 0, (
                    f"[{fixture_name}] '{cost.description}' の amount={cost.amount} が負の値"
                )

    @pytest.mark.parametrize("fixture_name", _FIXTURE_NAMES)
    def test_extras_no_empty_strings(self, fixture_name: str) -> None:
        """items_to_bring の item 名・dress_code・notes に空文字が含まれないこと"""
        raw_json = json.loads(
            (_RESPONSES_DIR / f"{fixture_name}.json").read_text(encoding="utf-8")
        )
        analysis = self._analyzer._convert_to_domain_model(raw_json)

        if analysis.extras is None:
            return

        for item in analysis.extras.items_to_bring:
            assert item.item.strip(), f"[{fixture_name}] items_to_bring に空文字の item が含まれる"

        for d in analysis.extras.dress_code:
            assert d.strip(), f"[{fixture_name}] dress_code に空文字が含まれる"

        for note in analysis.extras.notes:
            assert note.strip(), f"[{fixture_name}] notes に空文字が含まれる"


# ── 録画テスト（手動実行のみ）────────────────────────────────────────────────


@pytest.mark.manual
class TestRecordGeminiResponse:
    """実 Gemini API を呼び出してフィクスチャを録画する。

    実行例:
        PROJECT_ID=clearbag-dev \\
        uv run pytest tests/unit/test_gemini_extras_fixture.py::TestRecordGeminiResponse \\
            -m manual -v -s \\
            --pdf-path=path/to/sample.pdf \\
            --fixture-name=my_fixture
    """

    def test_record_response(self, request: pytest.FixtureRequest) -> None:
        """PDFを実 Gemini で解析してレスポンスをフィクスチャとして保存する"""
        import os

        import vertexai
        from vertexai.generative_models import GenerativeModel

        pdf_path = request.config.getoption("--pdf-path")
        fixture_name = request.config.getoption("--fixture-name")

        if not pdf_path or not fixture_name:
            pytest.skip("--pdf-path と --fixture-name の両方が必要です")

        pdf_file = Path(pdf_path)
        assert pdf_file.exists(), f"PDF が存在しない: {pdf_path}"

        project_id = os.environ["PROJECT_ID"]
        location = os.environ.get("VERTEX_AI_LOCATION", "us-central1")
        vertexai.init(project=project_id, location=location)
        model = GenerativeModel("gemini-2.5-pro")
        analyzer = GeminiDocumentAnalyzer(model=model)

        content = pdf_file.read_bytes()
        result = analyzer.analyze(content, "application/pdf", {})

        # レスポンスをフィクスチャとして保存するため、再度 JSON を取得する必要がある。
        # analyze() は内部で JSON をパースするので、ここでは直接 Gemini を呼んでrawを取る。
        import vertexai.preview.generative_models as generative_models
        from vertexai.generative_models import Part

        document_part = Part.from_data(data=content, mime_type="application/pdf")
        user_prompt = analyzer._build_user_prompt({}, [])
        HarmCategory = generative_models.HarmCategory
        HarmBlock = generative_models.HarmBlockThreshold
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlock.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlock.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlock.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlock.BLOCK_MEDIUM_AND_ABOVE,
        }
        response = model.generate_content(
            [document_part, user_prompt],
            generation_config={
                "max_output_tokens": 8192,
                "temperature": 0.2,
                "top_p": 0.95,
                "response_mime_type": "application/json",
            },
            safety_settings=safety_settings,
            stream=False,
        )
        raw_json = analyzer._parse_response(response.text)

        out_path = _RESPONSES_DIR / f"{fixture_name}.json"
        out_path.write_text(
            json.dumps(raw_json, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n✅ フィクスチャを保存しました: {out_path}")
        print(f"   次に {_EXPECTATIONS_DIR}/{fixture_name}.json を作成してください")

        # 解析結果のサマリーを表示
        analysis = result.analysis
        print(f"   category: {analysis.category}")
        print(f"   events:   {len(analysis.events)}")
        print(f"   tasks:    {len(analysis.tasks)}")
        if analysis.extras:
            print(f"   items:    {[i.item for i in analysis.extras.items_to_bring]}")
            print(f"   costs:    {[c.description for c in analysis.extras.costs]}")
            print(f"   notes:    {analysis.extras.notes}")

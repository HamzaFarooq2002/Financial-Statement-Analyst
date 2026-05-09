import sys
from collections.abc import Generator
from pathlib import Path

import pytest


def _clear_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]


@pytest.fixture
def e2e_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator:
    """Fresh app + isolated DB/uploads/exports; Gemini calls are patched."""
    db_file = tmp_path / "test.db"
    upload_dir = tmp_path / "uploads"
    export_dir = tmp_path / "exports"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.resolve().as_posix()}")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-for-ci")
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir.resolve()))
    monkeypatch.setenv("EXPORT_DIR", str(export_dir.resolve()))

    _clear_app_modules()

    from unittest.mock import patch

    from app.agents.ai_insight_generator import CFOInsight, CFOInsightResponse
    from app.agents.financial_metric_extraction_agent import (
        TARGET_METRICS,
        RawExtractedMetric,
        RawMetricExtractionResult,
    )

    def _metric_values(metric_name: str) -> tuple[str | None, str | None]:
        if metric_name == "eps":
            return "2.4", "2.1"
        return "10000", "9000"

    def fake_generate_parsed(
        _client,
        _model,
        _system_instruction,
        _user_text,
        response_model: type,
        *,
        task_label: str,
    ):
        _ = task_label

        from app.agents.document_metadata_extractor import DocumentMetadata
        from app.services.multi_year_analyzer import TrendSummary

        if response_model is DocumentMetadata:
            return DocumentMetadata(company_name="Test Bank", report_year=2024)

        if response_model is TrendSummary:
            return TrendSummary(
                headline="Cross-year trend overview",
                bullets=[
                    "Assets grew period over period.",
                    "Margins remain stable across samples.",
                    "Capital ratios show manageable movement.",
                ],
                confidence=0.82,
            )

        if response_model is RawMetricExtractionResult:
            metrics = []
            for name in TARGET_METRICS:
                cur, prev = _metric_values(name)
                metrics.append(
                    RawExtractedMetric(
                        metric_name=name,
                        current_year_value=cur,
                        previous_year_value=prev,
                        unit="PKR million",
                        source_page=1,
                        source_text=f"{name} from report",
                        confidence_score=0.85,
                    )
                )
            return RawMetricExtractionResult(metrics=metrics)
        if response_model is CFOInsightResponse:
            insights = [
                CFOInsight(
                    title=f"CFO insight {i + 1}",
                    type="neutral",
                    summary="The report does not clearly explain the cause.",
                    supporting_metrics=["total_assets", "roe"],
                    source_pages=[1],
                    confidence_score=0.75,
                )
                for i in range(5)
            ]
            return CFOInsightResponse(insights=insights)
        raise AssertionError(f"Unexpected response_model {response_model!r}")

    with (
        patch(
            "app.agents.financial_metric_extraction_agent.generate_parsed",
            side_effect=fake_generate_parsed,
        ),
        patch(
            "app.agents.ai_insight_generator.generate_parsed",
            side_effect=fake_generate_parsed,
        ),
        patch(
            "app.agents.document_metadata_extractor.generate_parsed",
            side_effect=fake_generate_parsed,
        ),
        patch(
            "app.services.multi_year_analyzer.generate_parsed",
            side_effect=fake_generate_parsed,
        ),
    ):
        from starlette.testclient import TestClient

        from app.main import create_app

        with TestClient(create_app()) as client:
            yield client

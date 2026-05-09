"""Multi-year dashboard alignment, YoY deltas, Gemini trend summary, and Excel export payload."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from google import genai
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.agents.gemini_llm import GeminiGenerationError, create_gemini_client, generate_parsed
from app.core.config import settings
from app.models.document import Document, ProcessingStatus
from app.services.excel_report_generator import generate_multi_year_excel


class TrendSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = Field(min_length=1)
    bullets: list[str] = Field(min_length=3, max_length=7)
    confidence: float = Field(ge=0.0, le=1.0)


def comparison_hash(document_ids: list[int]) -> str:
    payload = ",".join(str(i) for i in sorted(document_ids))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def artifact_dir(document_id: int) -> Path:
    return settings.export_dir / f"document_{document_id}"


def load_dashboard(document_id: int) -> dict[str, Any] | None:
    path = artifact_dir(document_id) / "dashboard.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_dashboards(document_ids: list[int]) -> list[tuple[int, dict[str, Any]]]:
    out: list[tuple[int, dict[str, Any]]] = []
    for doc_id in document_ids:
        dash = load_dashboard(doc_id)
        if dash is not None:
            out.append((doc_id, dash))
    return out


def _metric_sort_key(point: dict[str, Any]) -> tuple[int, int]:
    year = point.get("report_year")
    doc_id = point.get("document_id") or 0
    return (year if year is not None else -1, doc_id)


def compute_yoy_for_points(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach yoy_percent / yoy_amount vs prior period when sorted by year then document_id."""

    sorted_pts = sorted(points, key=_metric_sort_key)
    enriched: list[dict[str, Any]] = []
    for idx, p in enumerate(sorted_pts):
        clone = dict(p)
        if idx == 0:
            clone["yoy_percent"] = None
            clone["yoy_amount"] = None
        else:
            prev = sorted_pts[idx - 1]
            cur_v = p.get("value")
            prev_v = prev.get("value")
            if isinstance(cur_v, int | float) and isinstance(prev_v, int | float):
                clone["yoy_amount"] = float(cur_v) - float(prev_v)
                if prev_v != 0:
                    clone["yoy_percent"] = ((float(cur_v) - float(prev_v)) / abs(float(prev_v))) * 100
                else:
                    clone["yoy_percent"] = None
            else:
                clone["yoy_percent"] = None
                clone["yoy_amount"] = None
        enriched.append(clone)
    return enriched


def build_metric_series(dashboards: list[tuple[int, dict[str, Any]]]) -> list[dict[str, Any]]:
    """One series per metric_name across documents."""

    by_name: dict[str, dict[str, Any]] = {}

    for doc_id, dash in dashboards:
        year = dash.get("report_year")
        metrics = (dash.get("extracted_metrics") or {}).get("metrics") or []
        if not isinstance(metrics, list):
            continue
        for m in metrics:
            if not isinstance(m, dict):
                continue
            name = m.get("metric_name")
            if not name:
                continue
            unit = str(m.get("unit") or "")
            entry = by_name.setdefault(
                name,
                {"metric_name": name, "unit": unit, "points": []},
            )
            if unit and not entry.get("unit"):
                entry["unit"] = unit
            raw_val = m.get("current_year_value")
            val: float | None
            if raw_val is None:
                val = None
            elif isinstance(raw_val, int | float):
                val = float(raw_val)
            else:
                try:
                    val = float(raw_val)
                except (TypeError, ValueError):
                    val = None

            entry["points"].append(
                {
                    "document_id": doc_id,
                    "report_year": year,
                    "value": val,
                    "source_page": m.get("source_page"),
                }
            )

    series_list: list[dict[str, Any]] = []
    for _, series in sorted(by_name.items(), key=lambda kv: kv[0]):
        points = compute_yoy_for_points(series["points"])
        series_list.append(
            {
                "metric_name": series["metric_name"],
                "unit": series["unit"],
                "points": points,
            }
        )
    return series_list


def build_ratio_series(dashboards: list[tuple[int, dict[str, Any]]]) -> list[dict[str, Any]]:
    by_name: dict[str, dict[str, Any]] = {}

    for doc_id, dash in dashboards:
        year = dash.get("report_year")
        ratios = (dash.get("calculated_ratios") or {}).get("ratios") or []
        if not isinstance(ratios, list):
            continue
        for r in ratios:
            if not isinstance(r, dict):
                continue
            name = r.get("ratio_name")
            if not name:
                continue
            unit = str(r.get("unit") or "")
            entry = by_name.setdefault(
                name,
                {"ratio_name": name, "unit": unit, "points": []},
            )
            if unit and not entry.get("unit"):
                entry["unit"] = unit
            raw_val = r.get("value")
            val: float | None
            if raw_val is None:
                val = None
            elif isinstance(raw_val, int | float):
                val = float(raw_val)
            else:
                try:
                    val = float(raw_val)
                except (TypeError, ValueError):
                    val = None

            entry["points"].append(
                {
                    "document_id": doc_id,
                    "report_year": year,
                    "value": val,
                    "source_page": None,
                }
            )

    series_list: list[dict[str, Any]] = []
    for _, series in sorted(by_name.items(), key=lambda kv: kv[0]):
        points = compute_yoy_for_points(series["points"])
        series_list.append(
            {
                "ratio_name": series["ratio_name"],
                "unit": series["unit"],
                "points": points,
            }
        )
    return series_list


def generate_trend_summary(
    metric_series: list[dict[str, Any]],
    ratio_series: list[dict[str, Any]],
    *,
    client: genai.Client | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Produce headline + bullets via Gemini, or a deterministic fallback."""

    compact = {
        "metrics": [
            {
                "name": s["metric_name"],
                "unit": s["unit"],
                "timeline": [
                    {
                        "year": p.get("report_year"),
                        "value": p.get("value"),
                        "yoy_percent": p.get("yoy_percent"),
                    }
                    for p in sorted(s.get("points") or [], key=_metric_sort_key)
                ],
            }
            for s in metric_series[:20]
        ],
        "ratios": [
            {
                "name": s["ratio_name"],
                "unit": s["unit"],
                "timeline": [
                    {
                        "year": p.get("report_year"),
                        "value": p.get("value"),
                        "yoy_percent": p.get("yoy_percent"),
                    }
                    for p in sorted(s.get("points") or [], key=_metric_sort_key)
                ],
            }
            for s in ratio_series[:15]
        ],
    }

    summary_json = json.dumps(compact, ensure_ascii=False, indent=2)
    system_instruction = (
        "You are a CFO analyst. Given multi-year financial metric and ratio timelines extracted "
        "from annual reports, write a concise trend summary. "
        "Ground every bullet in the supplied numbers; do not invent figures. "
        "Respond only as JSON matching the schema."
    )

    if not settings.gemini_api_key:
        return _fallback_trend_summary(metric_series, ratio_series)

    gemini_client = client or create_gemini_client()
    gemini_model = model or settings.gemini_model

    try:
        parsed = generate_parsed(
            gemini_client,
            gemini_model,
            system_instruction,
            summary_json,
            TrendSummary,
            task_label="multi-year trend summary",
        )
        return {"headline": parsed.headline, "bullets": parsed.bullets, "confidence": parsed.confidence}
    except GeminiGenerationError:
        return _fallback_trend_summary(metric_series, ratio_series)


def _fallback_trend_summary(
    metric_series: list[dict[str, Any]],
    ratio_series: list[dict[str, Any]],
) -> dict[str, Any]:
    bullets: list[str] = []
    for s in metric_series[:3]:
        pts = sorted(s.get("points") or [], key=_metric_sort_key)
        if len(pts) < 2:
            continue
        last = pts[-1]
        prev = pts[-2]
        if last.get("value") is not None and prev.get("value") is not None:
            bullets.append(
                f"{s['metric_name']}: {prev.get('value')} to {last.get('value')} "
                f"({s.get('unit') or ''}) across periods."
            )
        if len(bullets) >= 5:
            break
    if len(bullets) < 3:
        for s in ratio_series[:3]:
            pts = sorted(s.get("points") or [], key=_metric_sort_key)
            if len(pts) < 2:
                continue
            last = pts[-1]
            prev = pts[-2]
            if last.get("value") is not None:
                bullets.append(
                    f"{s['ratio_name']} moved from {prev.get('value')} to {last.get('value')}."
                )
            if len(bullets) >= 5:
                break

    while len(bullets) < 3:
        bullets.append("Additional periods improve reliability of cross-year trends.")

    return {
        "headline": "Multi-year financial snapshot",
        "bullets": bullets[:7],
        "confidence": 0.35,
    }


def run_comparison(
    db: Session,
    document_ids: list[int],
    *,
    gemini_client: genai.Client | None = None,
) -> dict[str, Any]:
    """Validate IDs, build series + summary + Excel; return API payload."""

    unique_ids = sorted({int(i) for i in document_ids})
    if len(unique_ids) < 2:
        raise ValueError("At least two document IDs are required for comparison.")

    documents_meta: list[dict[str, Any]] = []
    dashboards: list[tuple[int, dict[str, Any]]] = []

    for doc_id in unique_ids:
        doc = db.get(Document, doc_id)
        if doc is None:
            raise ValueError(f"Document {doc_id} not found.")
        if doc.processing_status != ProcessingStatus.COMPLETED:
            raise ValueError(f"Document {doc_id} is not processed (status={doc.processing_status.value}).")

        dash = load_dashboard(doc_id)
        if dash is None:
            raise ValueError(f"Document {doc_id} has no dashboard export.")

        dashboards.append((doc_id, dash))
        documents_meta.append(
            {
                "document_id": doc_id,
                "file_name": doc.original_filename,
                "company_name": doc.company_name or dash.get("company_name"),
                "report_year": doc.report_year if doc.report_year is not None else dash.get("report_year"),
            }
        )

    metric_series = build_metric_series(dashboards)
    ratio_series = build_ratio_series(dashboards)
    trend_summary = generate_trend_summary(
        metric_series,
        ratio_series,
        client=gemini_client,
    )

    comp_hash = comparison_hash(unique_ids)
    comparisons_dir = settings.export_dir / "comparisons"
    comparisons_dir.mkdir(parents=True, exist_ok=True)
    excel_filename = f"comparison_{comp_hash}.xlsx"

    payload_for_excel = {
        "comparison_hash": comp_hash,
        "documents": documents_meta,
        "metric_series": metric_series,
        "ratio_series": ratio_series,
        "trend_summary": trend_summary,
    }

    excel_path = generate_multi_year_excel(
        payload_for_excel,
        output_dir=comparisons_dir,
        filename=excel_filename,
    )

    return {
        "comparison_hash": comp_hash,
        "documents": documents_meta,
        "metric_series": metric_series,
        "ratio_series": ratio_series,
        "trend_summary": trend_summary,
        "excel_download_path": excel_path,
    }

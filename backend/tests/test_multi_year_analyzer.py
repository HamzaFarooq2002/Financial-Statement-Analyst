"""Pure-unit coverage for multi-year series alignment and YoY math."""

import pytest

from app.services.multi_year_analyzer import build_metric_series, compute_yoy_for_points


def test_compute_yoy_for_points_orders_by_year_then_doc():
    pts = [
        {"document_id": 2, "report_year": 2023, "value": 110.0},
        {"document_id": 1, "report_year": 2022, "value": 100.0},
    ]
    out = compute_yoy_for_points(pts)
    assert out[0]["yoy_percent"] is None
    assert out[1]["yoy_percent"] == pytest.approx(10.0)


def test_build_metric_series_groups_metric_names():
    dashboards = [
        (
            10,
            {
                "report_year": 2022,
                "extracted_metrics": {
                    "metrics": [
                        {
                            "metric_name": "total_assets",
                            "current_year_value": 100,
                            "previous_year_value": 90,
                            "unit": "USD",
                            "source_page": 5,
                            "confidence_score": 0.9,
                        }
                    ]
                },
            },
        ),
        (
            11,
            {
                "report_year": 2023,
                "extracted_metrics": {
                    "metrics": [
                        {
                            "metric_name": "total_assets",
                            "current_year_value": 120,
                            "previous_year_value": 100,
                            "unit": "USD",
                            "source_page": 6,
                            "confidence_score": 0.92,
                        }
                    ]
                },
            },
        ),
    ]
    series = build_metric_series(dashboards)
    assert len(series) == 1
    assert series[0]["metric_name"] == "total_assets"
    assert len(series[0]["points"]) == 2

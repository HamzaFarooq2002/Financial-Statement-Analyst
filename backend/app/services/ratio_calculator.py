from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RatioCalculationError(Exception):
    """Raised when extracted metrics input cannot be interpreted."""


class RatioResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ratio_name: str
    value: float | None
    unit: str
    formula: str
    inputs: dict[str, float | None]
    missing_inputs: list[str] = Field(default_factory=list)
    explanation: str


class RatioCalculationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ratios: list[RatioResult]


def calculate_ratios(extracted_metrics: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    metrics = _index_metrics(extracted_metrics)

    results: list[RatioResult] = []
    for metric_name in metrics:
        results.append(_calculate_yoy_growth(metric_name, metrics))

    results.extend(
        [
            _calculate_roe(metrics),
            _calculate_roa(metrics),
            _calculate_cost_to_income(metrics),
            _calculate_equity_to_assets(metrics),
            _calculate_named_growth(
                ratio_name="deposit_growth",
                metric_name="deposits",
                metrics=metrics,
            ),
            _calculate_named_growth(
                ratio_name="advances_growth",
                metric_name="advances_or_loans",
                metrics=metrics,
            ),
        ]
    )

    return RatioCalculationResult(ratios=results).model_dump()


def _index_metrics(extracted_metrics: dict[str, Any]) -> dict[str, dict[str, float | None]]:
    raw_metrics = extracted_metrics.get("metrics")
    if not isinstance(raw_metrics, list):
        raise RatioCalculationError("Input must include a metrics list.")

    indexed: dict[str, dict[str, float | None]] = {}
    for metric in raw_metrics:
        if not isinstance(metric, dict):
            raise RatioCalculationError("Each metric must be a JSON object.")

        metric_name = metric.get("metric_name")
        if not isinstance(metric_name, str) or not metric_name:
            raise RatioCalculationError("Each metric must include metric_name.")

        indexed[metric_name] = {
            "current_year_value": _parse_optional_number(
                metric.get("current_year_value"),
                f"{metric_name}.current_year_value",
            ),
            "previous_year_value": _parse_optional_number(
                metric.get("previous_year_value"),
                f"{metric_name}.previous_year_value",
            ),
        }

    return indexed


def _parse_optional_number(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise RatioCalculationError(f"{field_name} must be numeric, not boolean.")
    if isinstance(value, int | float | Decimal):
        return float(value)
    if isinstance(value, str):
        normalized = value.strip().replace(",", "")
        if normalized in {"", "-", "--", "n/a", "N/A"}:
            return None
        try:
            return float(Decimal(normalized))
        except (InvalidOperation, ValueError) as exc:
            raise RatioCalculationError(f"{field_name} is not parseable as a number.") from exc

    raise RatioCalculationError(f"{field_name} is not parseable as a number.")


def _calculate_yoy_growth(
    metric_name: str,
    metrics: dict[str, dict[str, float | None]],
) -> RatioResult:
    current = _metric_value(metrics, metric_name, "current_year_value")
    previous = _metric_value(metrics, metric_name, "previous_year_value")
    return _growth_result(
        ratio_name=f"{metric_name}_yoy_growth",
        current=current,
        previous=previous,
        formula="((current_year_value - previous_year_value) / abs(previous_year_value)) * 100",
        inputs={
            f"{metric_name}.current_year_value": current,
            f"{metric_name}.previous_year_value": previous,
        },
    )


def _calculate_named_growth(
    ratio_name: str,
    metric_name: str,
    metrics: dict[str, dict[str, float | None]],
) -> RatioResult:
    current = _metric_value(metrics, metric_name, "current_year_value")
    previous = _metric_value(metrics, metric_name, "previous_year_value")
    return _growth_result(
        ratio_name=ratio_name,
        current=current,
        previous=previous,
        formula="((current_year_value - previous_year_value) / abs(previous_year_value)) * 100",
        inputs={
            f"{metric_name}.current_year_value": current,
            f"{metric_name}.previous_year_value": previous,
        },
    )


def _calculate_roe(metrics: dict[str, dict[str, float | None]]) -> RatioResult:
    profit = _metric_value(metrics, "net_profit_after_tax", "current_year_value")
    current_equity = _metric_value(metrics, "total_equity", "current_year_value")
    previous_equity = _metric_value(metrics, "total_equity", "previous_year_value")
    average_equity = _average(current_equity, previous_equity)

    return _percentage_result(
        ratio_name="roe",
        numerator=profit,
        denominator=average_equity,
        formula="net_profit_after_tax.current_year_value / average(total_equity.current_year_value, total_equity.previous_year_value) * 100",
        inputs={
            "net_profit_after_tax.current_year_value": profit,
            "total_equity.current_year_value": current_equity,
            "total_equity.previous_year_value": previous_equity,
            "average_total_equity": average_equity,
        },
    )


def _calculate_roa(metrics: dict[str, dict[str, float | None]]) -> RatioResult:
    profit = _metric_value(metrics, "net_profit_after_tax", "current_year_value")
    current_assets = _metric_value(metrics, "total_assets", "current_year_value")
    previous_assets = _metric_value(metrics, "total_assets", "previous_year_value")
    average_assets = _average(current_assets, previous_assets)

    return _percentage_result(
        ratio_name="roa",
        numerator=profit,
        denominator=average_assets,
        formula="net_profit_after_tax.current_year_value / average(total_assets.current_year_value, total_assets.previous_year_value) * 100",
        inputs={
            "net_profit_after_tax.current_year_value": profit,
            "total_assets.current_year_value": current_assets,
            "total_assets.previous_year_value": previous_assets,
            "average_total_assets": average_assets,
        },
    )


def _calculate_cost_to_income(metrics: dict[str, dict[str, float | None]]) -> RatioResult:
    expenses = _metric_value(metrics, "operating_expenses", "current_year_value")
    revenue = _metric_value(metrics, "revenue_or_markup_income", "current_year_value")
    numerator = abs(expenses) if expenses is not None else None

    return _percentage_result(
        ratio_name="cost_to_income_ratio",
        numerator=numerator,
        denominator=revenue,
        formula="abs(operating_expenses.current_year_value) / revenue_or_markup_income.current_year_value * 100",
        inputs={
            "operating_expenses.current_year_value": expenses,
            "abs_operating_expenses.current_year_value": numerator,
            "revenue_or_markup_income.current_year_value": revenue,
        },
    )


def _calculate_equity_to_assets(metrics: dict[str, dict[str, float | None]]) -> RatioResult:
    equity = _metric_value(metrics, "total_equity", "current_year_value")
    assets = _metric_value(metrics, "total_assets", "current_year_value")

    return _percentage_result(
        ratio_name="equity_to_assets_ratio",
        numerator=equity,
        denominator=assets,
        formula="total_equity.current_year_value / total_assets.current_year_value * 100",
        inputs={
            "total_equity.current_year_value": equity,
            "total_assets.current_year_value": assets,
        },
    )


def _growth_result(
    ratio_name: str,
    current: float | None,
    previous: float | None,
    formula: str,
    inputs: dict[str, float | None],
) -> RatioResult:
    missing_inputs = _missing_inputs(inputs)
    if missing_inputs:
        return _null_result(ratio_name, "%", formula, inputs, missing_inputs)
    if previous == 0:
        return _null_result(
            ratio_name,
            "%",
            formula,
            inputs,
            ["previous_year_value is zero"],
        )

    value = ((current - previous) / abs(previous)) * 100
    return RatioResult(
        ratio_name=ratio_name,
        value=_round_ratio(value),
        unit="%",
        formula=formula,
        inputs=inputs,
        missing_inputs=[],
        explanation="Calculated successfully.",
    )


def _percentage_result(
    ratio_name: str,
    numerator: float | None,
    denominator: float | None,
    formula: str,
    inputs: dict[str, float | None],
) -> RatioResult:
    missing_inputs = _missing_inputs(inputs)
    if missing_inputs:
        return _null_result(ratio_name, "%", formula, inputs, missing_inputs)
    if denominator == 0:
        return _null_result(ratio_name, "%", formula, inputs, ["denominator is zero"])

    value = (numerator / denominator) * 100
    return RatioResult(
        ratio_name=ratio_name,
        value=_round_ratio(value),
        unit="%",
        formula=formula,
        inputs=inputs,
        missing_inputs=[],
        explanation="Calculated successfully.",
    )


def _metric_value(
    metrics: dict[str, dict[str, float | None]],
    metric_name: str,
    period_key: str,
) -> float | None:
    return metrics.get(metric_name, {}).get(period_key)


def _average(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return (left + right) / 2


def _missing_inputs(inputs: dict[str, float | None]) -> list[str]:
    return [name for name, value in inputs.items() if value is None]


def _null_result(
    ratio_name: str,
    unit: str,
    formula: str,
    inputs: dict[str, float | None],
    missing_inputs: list[str],
) -> RatioResult:
    return RatioResult(
        ratio_name=ratio_name,
        value=None,
        unit=unit,
        formula=formula,
        inputs=inputs,
        missing_inputs=missing_inputs,
        explanation="Cannot calculate because required input is missing or invalid: "
        + ", ".join(missing_inputs),
    )


def _round_ratio(value: float) -> float:
    return round(value, 4)

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from google import genai
from pydantic import BaseModel, ConfigDict, Field

from app.agents.gemini_llm import GeminiGenerationError, create_gemini_client, generate_parsed
from app.core.config import settings


TARGET_METRICS = [
    "total_assets",
    "total_liabilities",
    "total_equity",
    "net_profit_after_tax",
    "revenue_or_markup_income",
    "operating_expenses",
    "eps",
    "cash_and_balances",
    "advances_or_loans",
    "deposits",
]

MetricName = Literal[
    "total_assets",
    "total_liabilities",
    "total_equity",
    "net_profit_after_tax",
    "revenue_or_markup_income",
    "operating_expenses",
    "eps",
    "cash_and_balances",
    "advances_or_loans",
    "deposits",
]


METRIC_GUIDANCE = {
    "total_assets": "Total assets / Total assets of the company or group.",
    "total_liabilities": "Total liabilities. Prefer an explicit total liabilities line.",
    "total_equity": "Total equity / total shareholders' equity / net assets.",
    "net_profit_after_tax": "Profit after tax / net profit after taxation / net income after tax.",
    "revenue_or_markup_income": "Revenue, net sales, turnover, markup earned, or markup income.",
    "operating_expenses": "Operating expenses, administrative expenses plus selling/distribution where shown as operating expense.",
    "eps": "Basic EPS / earnings per share attributable to ordinary shareholders.",
    "cash_and_balances": "Cash and balances with treasury/central bank or cash and cash equivalents.",
    "advances_or_loans": "Advances, loans, financing, or loans and advances to customers.",
    "deposits": "Customer deposits, deposits and other accounts, or total deposits.",
}


class FinancialMetricExtractionError(Exception):
    """Base exception for financial metric extraction failures."""


class GeminiExtractionError(FinancialMetricExtractionError):
    """Raised when the Gemini extraction request fails."""


class MetricValidationError(FinancialMetricExtractionError):
    """Raised when model output cannot be validated."""


class RelevantPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_number: int = Field(ge=1)
    text: str
    tables: list[Any] = Field(default_factory=list)


class RawExtractedMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_name: MetricName
    current_year_value: str | None
    previous_year_value: str | None
    unit: str
    source_page: int | None
    source_text: str
    confidence_score: float = Field(ge=0, le=1)


class RawMetricExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metrics: list[RawExtractedMetric]


class ExtractedMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_name: MetricName
    current_year_value: float | None
    previous_year_value: float | None
    unit: str
    source_page: int | None
    source_text: str
    confidence_score: float = Field(ge=0, le=1)


class FinancialMetricExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metrics: list[ExtractedMetric]


def extract_financial_metrics(
    relevant_pages: list[dict[str, Any]] | list[RelevantPage],
    client: genai.Client | None = None,
    model: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    agent = FinancialMetricExtractionAgent(client=client, model=model)
    return agent.extract(relevant_pages)


class FinancialMetricExtractionAgent:
    def __init__(self, client: genai.Client | None = None, model: str | None = None) -> None:
        self.client = client or create_gemini_client()
        self.model = model or settings.gemini_model

    def extract(
        self,
        relevant_pages: list[dict[str, Any]] | list[RelevantPage],
    ) -> dict[str, list[dict[str, Any]]]:
        pages = _validate_pages(relevant_pages)
        raw_result = self._extract_with_gemini(pages)
        result = _validate_and_normalize_metrics(raw_result, pages)
        return result.model_dump()

    def _extract_with_gemini(self, pages: list[RelevantPage]) -> RawMetricExtractionResult:
        try:
            return generate_parsed(
                self.client,
                self.model,
                _system_prompt(),
                _user_prompt(pages),
                RawMetricExtractionResult,
                task_label="financial metric extraction",
            )
        except GeminiGenerationError as exc:
            raise GeminiExtractionError(str(exc)) from exc


def _validate_pages(relevant_pages: list[dict[str, Any]] | list[RelevantPage]) -> list[RelevantPage]:
    if not relevant_pages:
        raise MetricValidationError("At least one relevant page is required.")

    try:
        pages = [
            page if isinstance(page, RelevantPage) else RelevantPage.model_validate(page)
            for page in relevant_pages
        ]
    except Exception as exc:
        raise MetricValidationError("Relevant pages are not valid.") from exc

    return pages


def _validate_and_normalize_metrics(
    raw_result: RawMetricExtractionResult,
    pages: list[RelevantPage],
) -> FinancialMetricExtractionResult:
    page_numbers = {page.page_number for page in pages}
    raw_by_name = {metric.metric_name: metric for metric in raw_result.metrics}
    normalized_metrics: list[ExtractedMetric] = []

    for metric_name in TARGET_METRICS:
        raw_metric = raw_by_name.get(metric_name) or RawExtractedMetric(
            metric_name=metric_name,
            current_year_value=None,
            previous_year_value=None,
            unit="unknown",
            source_page=None,
            source_text="",
            confidence_score=0,
        )

        if raw_metric.source_page is not None and raw_metric.source_page not in page_numbers:
            raise MetricValidationError(
                f"Metric {metric_name} references source_page {raw_metric.source_page}, "
                "which was not provided in relevant_pages."
            )

        normalized_metrics.append(
            ExtractedMetric(
                metric_name=metric_name,
                current_year_value=parse_financial_number(raw_metric.current_year_value),
                previous_year_value=parse_financial_number(raw_metric.previous_year_value),
                unit=raw_metric.unit.strip() or "unknown",
                source_page=raw_metric.source_page,
                source_text=raw_metric.source_text.strip(),
                confidence_score=raw_metric.confidence_score,
            )
        )

    return FinancialMetricExtractionResult(metrics=normalized_metrics)


def parse_financial_number(value: str | int | float | Decimal | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise MetricValidationError(f"Numeric value is not parseable: {value}")
    if isinstance(value, int | float | Decimal):
        return float(value)

    raw_value = str(value).strip()
    if raw_value in {"", "-", "--", "n/a", "N/A", "nil", "Nil"}:
        return None

    normalized = raw_value.replace("\u2212", "-").replace("%", "")
    currency_matches = list(
        re.finditer(r"(?i)(rs\.?|pkr|usd|eur|gbp|rupees?|dollars?)\s*", normalized)
    )
    search_text = normalized[currency_matches[-1].end() :] if currency_matches else normalized

    number_match = re.search(
        r"(?P<open>\()?\s*(?P<sign>[-+])?\s*"
        r"(?P<number>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)"
        r"\s*(?P<suffix>bn|billion|mn|million|m|thousand|k)?\s*(?P<close>\))?",
        search_text,
        flags=re.IGNORECASE,
    )
    if number_match is None:
        raise MetricValidationError(f"Numeric value is not parseable: {value}")

    number_text = number_match.group("number").replace(",", "")
    suffix = (number_match.group("suffix") or "").lower()
    multiplier = {
        "bn": Decimal("1000000000"),
        "billion": Decimal("1000000000"),
        "mn": Decimal("1000000"),
        "million": Decimal("1000000"),
        "m": Decimal("1000000"),
        "thousand": Decimal("1000"),
        "k": Decimal("1000"),
    }.get(suffix, Decimal("1"))

    is_negative = number_match.group("sign") == "-" or (
        number_match.group("open") == "(" and number_match.group("close") == ")"
    )

    try:
        number = Decimal(number_text) * multiplier
    except (InvalidOperation, ValueError) as exc:
        raise MetricValidationError(f"Numeric value is not parseable: {value}") from exc

    if is_negative:
        number *= Decimal("-1")

    return float(number)


def _system_prompt() -> str:
    metric_guidance = "\n".join(
        f"- {metric_name}: {guidance}" for metric_name, guidance in METRIC_GUIDANCE.items()
    )
    metric_names = ", ".join(TARGET_METRICS)

    return (
        "You are a financial statement extraction agent. Return strict JSON only. "
        "Extract values exactly from the provided annual report pages and do not calculate, "
        "infer, or derive missing values. Python code will validate and calculate later. "
        "Use null for missing numeric values. Use source_text as the shortest exact text span "
        "that supports the extracted values. Use source_page only from the provided pages. "
        "Return exactly these metric names: "
        f"{metric_names}.\n\nMetric guidance:\n{metric_guidance}"
    )


def _user_prompt(pages: list[RelevantPage]) -> str:
    page_blocks = []
    for page in pages:
        page_blocks.append(
            "\n".join(
                [
                    f"PAGE {page.page_number}",
                    "TEXT:",
                    page.text,
                    "TABLES:",
                    repr(page.tables),
                ]
            )
        )

    return (
        "Extract current year and previous year values for the requested metrics from these "
        "annual report pages. Preserve the unit or scale shown in the report, such as "
        "'PKR thousand', 'PKR million', 'USD million', or 'currency/share'. JSON output must "
        "match the schema exactly.\n\n"
        + "\n\n---\n\n".join(page_blocks)
    )

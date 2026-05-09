import json
from typing import Any, Literal

from google import genai
from pydantic import BaseModel, ConfigDict, Field

from app.agents.gemini_llm import GeminiGenerationError, create_gemini_client, generate_parsed
from app.core.config import settings


InsightType = Literal["positive", "warning", "risk", "neutral"]


class AIInsightGenerationError(Exception):
    """Base exception for AI insight generation failures."""


class GeminiInsightError(AIInsightGenerationError):
    """Raised when the Gemini insight request fails."""


class InsightValidationError(AIInsightGenerationError):
    """Raised when generated insights violate the input-grounding contract."""


class CFOInsight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    type: InsightType
    summary: str = Field(min_length=1)
    supporting_metrics: list[str] = Field(default_factory=list)
    source_pages: list[int] = Field(default_factory=list)
    confidence_score: float = Field(ge=0, le=1)


class CFOInsightResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    insights: list[CFOInsight] = Field(min_length=5, max_length=5)


def generate_ai_insights(
    extracted_metrics: dict[str, Any],
    calculated_ratios: dict[str, Any],
    client: genai.Client | None = None,
    model: str | None = None,
) -> list[dict[str, Any]]:
    generator = AIInsightGenerator(client=client, model=model)
    return generator.generate(extracted_metrics, calculated_ratios)


class AIInsightGenerator:
    def __init__(self, client: genai.Client | None = None, model: str | None = None) -> None:
        self.client = client or create_gemini_client()
        self.model = model or settings.gemini_model

    def generate(
        self,
        extracted_metrics: dict[str, Any],
        calculated_ratios: dict[str, Any],
    ) -> list[dict[str, Any]]:
        context = _build_financial_context(extracted_metrics, calculated_ratios)
        raw_response = self._generate_with_gemini(context)
        validated = _validate_insights(raw_response, context)
        return [insight.model_dump() for insight in validated.insights]

    def _generate_with_gemini(self, context: dict[str, Any]) -> CFOInsightResponse:
        try:
            return generate_parsed(
                self.client,
                self.model,
                _system_prompt(),
                _user_prompt(context),
                CFOInsightResponse,
                task_label="CFO insight generation",
            )
        except GeminiGenerationError as exc:
            raise GeminiInsightError(str(exc)) from exc


def _build_financial_context(
    extracted_metrics: dict[str, Any],
    calculated_ratios: dict[str, Any],
) -> dict[str, Any]:
    metrics = extracted_metrics.get("metrics")
    ratios = calculated_ratios.get("ratios")

    if not isinstance(metrics, list):
        raise InsightValidationError("extracted_metrics must include a metrics list.")
    if not isinstance(ratios, list):
        raise InsightValidationError("calculated_ratios must include a ratios list.")

    metric_names: set[str] = set()
    ratio_names: set[str] = set()
    source_pages: set[int] = set()

    for metric in metrics:
        if not isinstance(metric, dict):
            raise InsightValidationError("Each extracted metric must be a JSON object.")

        metric_name = metric.get("metric_name")
        if not isinstance(metric_name, str) or not metric_name:
            raise InsightValidationError("Each extracted metric must include metric_name.")
        metric_names.add(metric_name)

        source_page = metric.get("source_page")
        if isinstance(source_page, int):
            source_pages.add(source_page)
        elif source_page is not None:
            raise InsightValidationError(f"{metric_name}.source_page must be an integer or null.")

    for ratio in ratios:
        if not isinstance(ratio, dict):
            raise InsightValidationError("Each calculated ratio must be a JSON object.")

        ratio_name = ratio.get("ratio_name")
        if not isinstance(ratio_name, str) or not ratio_name:
            raise InsightValidationError("Each calculated ratio must include ratio_name.")
        ratio_names.add(ratio_name)

    return {
        "metrics": metrics,
        "ratios": ratios,
        "allowed_supporting_metrics": sorted(metric_names | ratio_names),
        "allowed_source_pages": sorted(source_pages),
    }


def _validate_insights(
    response: CFOInsightResponse,
    context: dict[str, Any],
) -> CFOInsightResponse:
    allowed_supporting_metrics = set(context["allowed_supporting_metrics"])
    allowed_source_pages = set(context["allowed_source_pages"])

    for insight in response.insights:
        unknown_metrics = [
            metric for metric in insight.supporting_metrics if metric not in allowed_supporting_metrics
        ]
        if unknown_metrics:
            raise InsightValidationError(
                "Insight references supporting metrics not present in inputs: "
                + ", ".join(unknown_metrics)
            )

        unknown_pages = [page for page in insight.source_pages if page not in allowed_source_pages]
        if unknown_pages:
            raise InsightValidationError(
                "Insight references source pages not present in extracted metrics: "
                + ", ".join(str(page) for page in unknown_pages)
            )

    return response


def _system_prompt() -> str:
    return (
        "You are a CFO-style financial analyst. Generate exactly 5 concise insights in strict "
        "JSON matching the provided schema. Do not invent facts, causes, management actions, "
        "macroeconomic context, or explanations. Only use the extracted metrics, calculated "
        "ratios, source_text, source_page, formulas, and missing-input explanations provided "
        "by the user. If a cause is unknown or not directly supported by the provided report "
        'text, say exactly: "The report does not clearly explain the cause." '
        "supporting_metrics must contain only provided metric_name or ratio_name values. "
        "source_pages must contain only source pages found in the extracted metrics. "
        "Use neutral when the data is incomplete or mixed."
    )


def _user_prompt(context: dict[str, Any]) -> str:
    return (
        "Create 5 CFO-style insights from the following validated financial data. "
        "Do not calculate new ratios. Do not cite pages unless they appear in "
        "allowed_source_pages. Do not use supporting metric names unless they appear in "
        "allowed_supporting_metrics.\n\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
    )

"""
Document summarizer module.

TemplateSummarizer — rule-based, zero-latency, no external dependencies.
LLMSummarizer      — stub for drop-in LLM integration (OpenAI / Anthropic / local).

Both implement the same interface:
    generate(request, risk_score, recommendation, flags) -> str
"""

from typing import List, Optional
from .schemas import ScoringRequest, Recommendation


# ---------------------------------------------------------------------------
# Template Summarizer (production default)
# ---------------------------------------------------------------------------

class TemplateSummarizer:
    """
    Generates natural-language summaries using deterministic templates.

    Templates are keyed by document type + recommendation tier.
    Fills in dynamic values from the request payload and scoring results.
    """

    _INTROS = {
        "invoice":  "Invoice",
        "contract": "Contract",
        "receipt":  "Receipt",
        "report":   "Report",
        "claim":    "Claim",
        "default":  "Document",
    }

    _OUTCOME_TEMPLATES = {
        Recommendation.APPROVE: "{label} {doc_id} processed successfully. {detail} No significant issues detected.",
        Recommendation.REVIEW:  "{label} {doc_id} requires manual review. {detail} {flag_summary}",
        Recommendation.REJECT:  "{label} {doc_id} rejected due to risk factors. {detail} {flag_summary}",
    }

    def generate(
        self,
        request: ScoringRequest,
        risk_score: float,
        recommendation: Recommendation,
        flags: List[str],
    ) -> str:
        data = request.standardized_data
        doc_type = str(data.get("type", "default")).lower()
        label = self._INTROS.get(doc_type, self._INTROS["default"])

        # Build detail clause
        detail_parts = []
        if "vendor" in data or "merchant" in data:
            party = data.get("vendor") or data.get("merchant")
            detail_parts.append(f"from {party}")
        if "amount" in data or "total" in data:
            amt = data.get("amount") or data.get("total")
            currency = data.get("currency", "")
            try:
                detail_parts.append(f"for {currency} {float(amt):,.2f}".strip())
            except (TypeError, ValueError):
                pass
        if "date" in data:
            detail_parts.append(f"dated {data['date']}")

        detail = (" ".join(detail_parts) + ".").capitalize() if detail_parts else ""

        # Flag summary (top 2 flags, capped for readability)
        flag_summary = ""
        if flags:
            top = flags[:2]
            flag_summary = "Issues: " + "; ".join(top) + "."

        summary = self._OUTCOME_TEMPLATES[recommendation].format(
            label=label,
            doc_id=request.document_id,
            detail=detail,
            flag_summary=flag_summary,
        ).strip()

        # Append risk context for non-approve outcomes
        if recommendation != Recommendation.APPROVE:
            summary += f" (Risk score: {risk_score:.2f})"

        return summary


# ---------------------------------------------------------------------------
# LLM Summarizer stub — swap TemplateSummarizer for this when ready
# ---------------------------------------------------------------------------

class LLMSummarizer:
    """
    Generates summaries via an LLM API call.

    To activate:
      1. Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable.
      2. Replace `TemplateSummarizer` in ScoringService with `LLMSummarizer`.

    This stub shows the expected call pattern for Anthropic's Messages API.
    """

    SYSTEM_PROMPT = (
        "You are a document processing assistant. Given structured document data, "
        "a risk score, and a recommendation, write a concise one-to-two sentence summary "
        "suitable for an operations team. Be factual, neutral in tone, and highlight any flags."
    )

    def __init__(self, model: str = "claude-3-5-sonnet-20241022", max_tokens: int = 120):
        self.model = model
        self.max_tokens = max_tokens

    def generate(
        self,
        request: ScoringRequest,
        risk_score: float,
        recommendation: Recommendation,
        flags: List[str],
    ) -> str:
        import os
        
        # Check if API key is set
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            # Fall back to template summarizer if API key is missing
            return TemplateSummarizer().generate(request, risk_score, recommendation, flags)
        
        try:
            import anthropic
            
            user_prompt = (
                f"Document ID: {request.document_id}\n"
                f"Data: {request.standardized_data}\n"
                f"Validation valid: {request.validation_result.is_valid}\n"
                f"Risk score: {risk_score:.3f}\n"
                f"Recommendation: {recommendation.value}\n"
                f"Flags: {flags}\n\n"
                "Write a concise operational summary."
            )
            client = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return message.content[0].text.strip()
        except (TypeError, ImportError, Exception) as e:
            # Fall back to template summarizer on any error
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"LLM API failed ({type(e).__name__}), using template summarizer: {str(e)}")
            return TemplateSummarizer().generate(request, risk_score, recommendation, flags)

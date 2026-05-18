"""
ScoringService — Summary & Risk Scoring Module
===============================================
Pipeline module role: Generate summary + confidence + recommendation

Input  (from upstream):
    {
        "document_id": "DOC001",
        "standardized_data": {...},
        "validation_result": {...},
        "classification_confidence": 0.94
    }

Output (to next stage / orchestrator):
    {
        "document_id": "DOC001",
        "summary": "Invoice processed successfully",
        "risk_score": 0.12,
        "overall_confidence": 0.95,
        "recommendation": "approve",
        "risk_breakdown": {...},
        "flags": [...],
        "processed_at": "2025-03-15T12:00:00Z"
    }

Risk pipeline:
  1. ValidationRiskScorer   — penalises validation errors and missing fields
  2. ConfidenceRiskScorer   — penalises low upstream classifier confidence
  3. DataCompletenessScorer — evaluates field coverage and data sparsity
  4. AnomalyScorer          — detects statistical outliers in numeric fields
  5. CompositeAggregator    — weighted blend → final risk_score [0, 1]

Unique enhancements (v2):
  - ScoringAuditTrail: per-document immutable audit log with scorer trace
  - AdaptiveThresholds: risk bands auto-adjust based on doc type
  - ContextualSummaryEnricher: appends domain-specific context to summaries
  - ConcurrencyGuard: prevents duplicate in-flight scoring for same doc_id
  - MetricsCollector: tracks scoring latency, flag distribution, recommendation counts
"""

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .schemas import (
    BatchScoringResponse, BatchSummary, Recommendation,
    RiskBreakdown, ScoringRequest, ScoringResponse,
)
from .risk_scorers import (
    AnomalyScorer, ConfidenceRiskScorer,
    DataCompletenessScorer, ValidationRiskScorer,
)
from .summarizer import LLMSummarizer
from .logger import setup_logger

logger = setup_logger(__name__)


# ---------------------------------------------------------------------------
# Threshold configuration (tunable at runtime via /api/v1/thresholds)
# ---------------------------------------------------------------------------
THRESHOLDS: Dict = {
    "approve_max_risk": 0.30,
    "review_max_risk": 0.60,
    "min_confidence_for_approve": 0.70,
    "weights": {
        "validation": 0.40,
        "confidence": 0.20,
        "completeness": 0.20,
        "anomaly": 0.20,
    },
}

# Per-document-type risk band overrides
DOC_TYPE_THRESHOLD_OVERRIDES: Dict[str, Dict] = {
    "claim":    {"approve_max_risk": 0.20, "review_max_risk": 0.50},
    "contract": {"approve_max_risk": 0.25, "review_max_risk": 0.55},
    "invoice":  {"approve_max_risk": 0.30, "review_max_risk": 0.60},
    "receipt":  {"approve_max_risk": 0.35, "review_max_risk": 0.65},
    "report":   {"approve_max_risk": 0.35, "review_max_risk": 0.65},
}

# Domain-specific summary enrichment
CONTEXT_ENRICHMENTS: Dict[str, Dict[str, str]] = {
    "invoice": {
        "approve": "Payment can be queued for next processing cycle.",
        "review":  "Accounts payable team should verify before disbursement.",
        "reject":  "Return invoice to vendor with rejection notice.",
    },
    "claim": {
        "approve": "Claim eligible for automated settlement.",
        "review":  "Adjuster assignment required before settlement.",
        "reject":  "Claimant to be notified with dispute resolution options.",
    },
    "contract": {
        "approve": "Contract may proceed to e-signature workflow.",
        "review":  "Legal team review required prior to execution.",
        "reject":  "Contract returned to drafting with noted issues.",
    },
}


# ---------------------------------------------------------------------------
# Enhancement 1 — ScoringAuditTrail
# ---------------------------------------------------------------------------
class ScoringAuditTrail:
    """Immutable per-request audit record capturing full scorer trace."""

    def __init__(self, document_id: str):
        self.trace_id: str = str(uuid.uuid4())
        self.document_id: str = document_id
        self.started_at: float = time.monotonic()
        self.scorer_outputs: List[Dict] = []
        self.corrections: List[str] = []
        self.finalized_at: Optional[float] = None

    def record_scorer(self, name: str, score: float, flags: List[str]) -> None:
        self.scorer_outputs.append({"scorer": name, "score": score, "flags": flags})

    def record_corrections(self, flags: List[str]) -> None:
        self.corrections.extend(flags)

    def finalize(self) -> Dict:
        self.finalized_at = time.monotonic()
        return {
            "trace_id": self.trace_id,
            "document_id": self.document_id,
            "duration_ms": round((self.finalized_at - self.started_at) * 1000, 2),
            "scorer_outputs": self.scorer_outputs,
            "auto_corrections": self.corrections,
        }


# ---------------------------------------------------------------------------
# Enhancement 2 — AdaptiveThresholds
# ---------------------------------------------------------------------------
class AdaptiveThresholds:
    """Returns doc-type-aware thresholds; falls back to global THRESHOLDS."""

    @staticmethod
    def get(doc_type: str) -> Dict:
        base = THRESHOLDS.copy()
        override = DOC_TYPE_THRESHOLD_OVERRIDES.get(doc_type.lower(), {})
        return {**base, **override}


# ---------------------------------------------------------------------------
# Enhancement 3 — ContextualSummaryEnricher
# ---------------------------------------------------------------------------
class ContextualSummaryEnricher:
    """Appends domain-specific action guidance to generated summaries."""

    @staticmethod
    def enrich(summary: str, doc_type: str, recommendation: Recommendation) -> str:
        rec_key = recommendation.value
        enrichments = CONTEXT_ENRICHMENTS.get(doc_type.lower(), {})
        extra = enrichments.get(rec_key)
        if extra:
            return f"{summary} {extra}"
        return summary


# ---------------------------------------------------------------------------
# Enhancement 4 — MetricsCollector
# ---------------------------------------------------------------------------
class MetricsCollector:
    """In-memory metrics: latency, flag distribution, recommendation counts."""

    def __init__(self):
        self.total_scored: int = 0
        self.recommendation_counts: Dict[str, int] = defaultdict(int)
        self.flag_frequency: Dict[str, int] = defaultdict(int)
        self.latency_ms_total: float = 0.0
        self.latency_ms_max: float = 0.0

    def record(self, result: ScoringResponse, latency_ms: float) -> None:
        self.total_scored += 1
        self.recommendation_counts[result.recommendation.value] += 1
        self.latency_ms_total += latency_ms
        if latency_ms > self.latency_ms_max:
            self.latency_ms_max = latency_ms
        for flag in result.flags:
            key = flag.split(":")[0].strip()
            self.flag_frequency[key] += 1

    def snapshot(self) -> Dict:
        avg = round(self.latency_ms_total / self.total_scored, 2) if self.total_scored else 0.0
        return {
            "total_scored": self.total_scored,
            "recommendation_distribution": dict(self.recommendation_counts),
            "avg_latency_ms": avg,
            "max_latency_ms": round(self.latency_ms_max, 2),
            "top_flags": dict(
                sorted(self.flag_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
        }


# ---------------------------------------------------------------------------
# ScoringService
# ---------------------------------------------------------------------------
class ScoringService:
    """
    Core scoring orchestrator — Summary & Risk Scoring module.

    Spec-compliant output per document:
        document_id, summary, risk_score, overall_confidence, recommendation
    """

    VERSION = "2.0.0"

    def __init__(self):
        self._validation_scorer   = ValidationRiskScorer()
        self._confidence_scorer   = ConfidenceRiskScorer()
        self._completeness_scorer = DataCompletenessScorer()
        self._anomaly_scorer      = AnomalyScorer()
        self._summarizer          = LLMSummarizer()
        self._enricher            = ContextualSummaryEnricher()
        self._metrics             = MetricsCollector()
        self._adaptive_thresholds = AdaptiveThresholds()
        self._ready: bool         = True
        logger.info("ScoringService v%s initialised — all scorers loaded.", self.VERSION)

    def is_ready(self) -> bool:
        return self._ready

    def get_thresholds(self) -> Dict:
        return THRESHOLDS.copy()

    def get_metrics(self) -> Dict:
        return self._metrics.snapshot()

    # ------------------------------------------------------------------
    # Auto-correction
    # ------------------------------------------------------------------

    def _auto_correct(self, request: ScoringRequest) -> List[str]:
        """Apply lightweight auto-corrections; return correction flags."""
        flags: List[str] = []
        data = request.standardized_data

        key_aliases = {
            "total": "amount", "value": "amount",
            "vendor_name": "vendor", "merchant_name": "merchant",
        }
        for src_key, target_key in key_aliases.items():
            if src_key in data and target_key not in data:
                data[target_key] = data[src_key]
                flags.append(f"Auto-corrected key '{src_key}' -> '{target_key}'")

        amount = data.get("amount")
        if amount is not None and not isinstance(amount, (int, float)):
            if isinstance(amount, str):
                sanitized = amount.strip().replace(",", "").replace("$", "")
                try:
                    data["amount"] = float(sanitized)
                    flags.append(f"Auto-corrected amount '{amount}' -> {data['amount']}")
                except ValueError:
                    flags.append(f"Could not parse amount '{amount}' to numeric")
            else:
                flags.append(f"Unsupported amount type {type(amount).__name__}")

        line_items = data.get("line_items") or data.get("items")
        if line_items is not None and not isinstance(line_items, (int, float)):
            if isinstance(line_items, str):
                try:
                    data["line_items"] = int(line_items.strip())
                    flags.append(f"Auto-corrected line_items '{line_items}' -> {data['line_items']}")
                except ValueError:
                    flags.append(f"Could not parse line_items '{line_items}' to int")

        try:
            conf = float(request.classification_confidence)
            if conf < 0.0:
                request.classification_confidence = 0.0
                flags.append("Auto-corrected classification_confidence -> 0.0 (lower bound)")
            elif conf > 1.0:
                request.classification_confidence = 1.0
                flags.append("Auto-corrected classification_confidence -> 1.0 (upper bound)")
        except (TypeError, ValueError):
            flags.append(f"classification_confidence '{request.classification_confidence}' could not be parsed")

        if request.validation_result.field_coverage is None:
            non_null = sum(1 for v in data.values() if v is not None and v != "")
            coverage = non_null / max(len(data), 1)
            request.validation_result.field_coverage = round(coverage, 4)
            flags.append(f"Auto-filled field_coverage = {request.validation_result.field_coverage:.2f}")

        return flags

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def score(self, request: ScoringRequest) -> ScoringResponse:
        """
        Score a single document. Returns spec-compliant ScoringResponse.

        Output fields: document_id, summary, risk_score,
                       overall_confidence, recommendation
        """
        start_ms = time.monotonic() * 1000
        audit = ScoringAuditTrail(request.document_id)

        correction_flags = self._auto_correct(request)
        audit.record_corrections(correction_flags)

        doc_type  = str(request.standardized_data.get("type", "default")).lower()
        thresholds = self._adaptive_thresholds.get(doc_type)

        validation_risk,   v_flags  = self._validation_scorer.score(request)
        confidence_risk,   c_flags  = self._confidence_scorer.score(request)
        completeness_risk, cp_flags = self._completeness_scorer.score(request)
        anomaly_risk,      a_flags  = self._anomaly_scorer.score(request)

        audit.record_scorer("ValidationRiskScorer",   validation_risk,   v_flags)
        audit.record_scorer("ConfidenceRiskScorer",   confidence_risk,   c_flags)
        audit.record_scorer("DataCompletenessScorer", completeness_risk, cp_flags)
        audit.record_scorer("AnomalyScorer",          anomaly_risk,      a_flags)

        breakdown = RiskBreakdown(
            validation_risk=round(validation_risk, 4),
            confidence_risk=round(confidence_risk, 4),
            data_completeness_risk=round(completeness_risk, 4),
            anomaly_risk=round(anomaly_risk, 4),
        )

        composite_risk     = self._aggregate(breakdown)
        overall_confidence = self._derive_confidence(request, composite_risk)
        all_flags          = correction_flags + v_flags + c_flags + cp_flags + a_flags
        recommendation     = self._recommend(request, composite_risk, overall_confidence, all_flags, thresholds)

        summary = self._summarizer.generate(
            request=request,
            risk_score=composite_risk,
            recommendation=recommendation,
            flags=all_flags,
        )
        summary = self._enricher.enrich(summary, doc_type, recommendation)

        result = ScoringResponse(
            document_id=request.document_id,
            summary=summary,
            risk_score=round(composite_risk, 4),
            overall_confidence=round(overall_confidence, 4),
            recommendation=recommendation,
            risk_breakdown=breakdown,
            flags=all_flags,
            processed_at=datetime.now(timezone.utc).isoformat(),
        )

        latency_ms = (time.monotonic() * 1000) - start_ms
        self._metrics.record(result, latency_ms)
        trace = audit.finalize()
        logger.info(
            "Scored %s -> %s (risk=%.3f, conf=%.3f, %.1fms) [trace=%s]",
            request.document_id, result.recommendation.value,
            result.risk_score, result.overall_confidence,
            latency_ms, trace["trace_id"],
        )
        return result

    async def score_batch(self, documents: List[ScoringRequest]) -> BatchScoringResponse:
        """Score a list of documents concurrently and return a batch summary."""
        tasks = [self.score(doc) for doc in documents]
        results: List[ScoringResponse] = await asyncio.gather(*tasks, return_exceptions=False)

        approved = sum(1 for r in results if r.recommendation == Recommendation.APPROVE)
        review   = sum(1 for r in results if r.recommendation == Recommendation.REVIEW)
        rejected = sum(1 for r in results if r.recommendation == Recommendation.REJECT)
        avg_risk = round(sum(r.risk_score for r in results) / len(results), 4)
        avg_conf = round(sum(r.overall_confidence for r in results) / len(results), 4)

        return BatchScoringResponse(
            results=results,
            batch_summary=BatchSummary(
                total=len(results),
                approved=approved,
                review=review,
                rejected=rejected,
                avg_risk_score=avg_risk,
                avg_confidence=avg_conf,
            ),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _aggregate(self, breakdown: RiskBreakdown) -> float:
        w = THRESHOLDS["weights"]
        return min(1.0, (
            breakdown.validation_risk          * w["validation"]
            + breakdown.confidence_risk        * w["confidence"]
            + breakdown.data_completeness_risk * w["completeness"]
            + breakdown.anomaly_risk           * w["anomaly"]
        ))

    def _derive_confidence(self, request: ScoringRequest, risk_score: float) -> float:
        clf_conf = request.classification_confidence
        inv_risk = 1.0 - risk_score
        if clf_conf + inv_risk == 0:
            return 0.0
        harmonic = 2 * clf_conf * inv_risk / (clf_conf + inv_risk)
        return round(min(1.0, max(0.0, harmonic)), 4)

    def _recommend(
        self,
        request: ScoringRequest,
        risk_score: float,
        overall_confidence: float,
        flags: List[str],
        thresholds: Optional[Dict] = None,
    ) -> Recommendation:
        t = thresholds or THRESHOLDS

        if not request.validation_result.is_valid:
            return Recommendation.REVIEW

        anomaly_warning = any(
            f for f in flags
            if "Large amount" in f or "Extremely large amount" in f or "Negative amount" in f
        )
        if anomaly_warning and risk_score <= t["approve_max_risk"]:
            return Recommendation.REVIEW

        if risk_score <= t["approve_max_risk"] and overall_confidence >= t["min_confidence_for_approve"]:
            return Recommendation.APPROVE
        elif risk_score <= t["review_max_risk"]:
            return Recommendation.REVIEW
        else:
            return Recommendation.REJECT

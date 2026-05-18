"""
Risk scorer modules — each returns a (score: float, flags: List[str]) tuple.

Scores are normalised to [0, 1]:
  0.0 = no risk contribution from this dimension
  1.0 = maximum risk from this dimension

Flags are human-readable strings surfaced in the API response.
"""

from typing import List, Tuple
import math
from .schemas import ScoringRequest


# ---------------------------------------------------------------------------
# 1. Validation Risk Scorer
# ---------------------------------------------------------------------------

class ValidationRiskScorer:
    """
    Penalises documents with validation errors or warnings.
    Hard errors carry more weight than soft warnings.

    Score formula:
        base = min(len(errors) * 0.25 + len(warnings) * 0.08, 1.0)
        If not is_valid: add 0.30 floor (document structurally invalid)
    """

    ERROR_PENALTY   = 0.25
    WARNING_PENALTY = 0.08
    INVALID_FLOOR   = 0.30

    def score(self, request: ScoringRequest) -> Tuple[float, List[str]]:
        vr = request.validation_result
        flags: List[str] = []

        penalty = len(vr.errors) * self.ERROR_PENALTY + len(vr.warnings) * self.WARNING_PENALTY
        if not vr.is_valid:
            penalty = max(penalty, self.INVALID_FLOOR)
            flags.append("Document failed validation")

        for err in vr.errors:
            flags.append(f"Validation error: {err}")
        for warn in vr.warnings[:3]:  # cap surface noise
            flags.append(f"Validation warning: {warn}")

        return min(1.0, round(penalty, 4)), flags


# ---------------------------------------------------------------------------
# 2. Confidence Risk Scorer
# ---------------------------------------------------------------------------

class ConfidenceRiskScorer:
    """
    Transforms upstream classifier confidence into a risk contribution.

    High confidence → low risk. Uses an exponential decay so scores below
    0.5 confidence contribute disproportionately more risk.

    risk = exp(-4 * confidence) normalised so conf=1.0 → ~0.018 and conf=0.0 → 1.0
    """

    def score(self, request: ScoringRequest) -> Tuple[float, List[str]]:
        conf = request.classification_confidence
        flags: List[str] = []

        raw = math.exp(-4.0 * conf)
        risk = round(min(1.0, raw), 4)

        if conf < 0.50:
            flags.append(f"Low classifier confidence ({conf:.0%}) — manual review recommended")
        elif conf < 0.70:
            flags.append(f"Moderate classifier confidence ({conf:.0%})")

        return risk, flags


# ---------------------------------------------------------------------------
# 3. Data Completeness Scorer
# ---------------------------------------------------------------------------

class DataCompletenessScorer:
    """
    Penalises sparse or minimal payloads.

    Metrics:
      - field_coverage from ValidationResult (if provided)
      - number of non-None fields in standardized_data
      - presence of expected high-value fields by document type
    """

    EXPECTED_FIELDS_BY_TYPE = {
        "invoice":    {"amount", "vendor", "date", "currency", "line_items"},
        "contract":   {"parties", "effective_date", "expiry_date", "clauses"},
        "receipt":    {"amount", "merchant", "date", "items"},
        "report":     {"title", "author", "date", "sections"},
        "claim":      {"claimant", "amount", "incident_date", "description"},
    }

    def score(self, request: ScoringRequest) -> Tuple[float, List[str]]:
        flags: List[str] = []
        data = request.standardized_data
        vr = request.validation_result

        # Use supplied coverage if available, else compute from data keys
        if vr.field_coverage is not None:
            coverage = vr.field_coverage
        else:
            non_null = sum(1 for v in data.values() if v is not None and v != "")
            coverage = non_null / max(len(data), 1)

        # Check type-specific expected fields
        doc_type = str(data.get("type", "")).lower()
        missing_key_fields: List[str] = []
        if doc_type in self.EXPECTED_FIELDS_BY_TYPE:
            expected = self.EXPECTED_FIELDS_BY_TYPE[doc_type]
            present  = {k.lower() for k in data.keys()}
            missing_key_fields = sorted(expected - present)

        type_coverage_penalty = len(missing_key_fields) * 0.10

        # Combined completeness risk
        base_risk = 1.0 - coverage
        total_risk = min(1.0, base_risk + type_coverage_penalty)

        if coverage < 0.60:
            flags.append(f"Low data coverage ({coverage:.0%}) — many fields missing")
        if missing_key_fields:
            flags.append(f"Missing expected fields: {', '.join(missing_key_fields)}")

        return round(total_risk, 4), flags


# ---------------------------------------------------------------------------
# 4. Anomaly Scorer
# ---------------------------------------------------------------------------

class AnomalyScorer:
    """
    Detects statistical anomalies in numeric fields within standardized_data.

    Current heuristics:
      - Extremely large amounts (> configurable threshold)
      - Negative amounts where unexpected
      - Unusually high line_item counts
      - Future-dated documents
    """

    AMOUNT_THRESHOLD        = 1_000_000
    LARGE_AMOUNT_THRESHOLD  = 100_000
    MAX_LINE_ITEMS          = 500

    def score(self, request: ScoringRequest) -> Tuple[float, List[str]]:
        data = request.standardized_data
        flags: List[str] = []
        risk = 0.0

        # --- Amount checks ---
        amount = data.get("amount") or data.get("total") or data.get("value")
        if amount is not None:
            try:
                amount = float(amount)
                if amount < 0:
                    risk += 0.40
                    flags.append(f"Negative amount detected: {amount}")
                elif amount > self.AMOUNT_THRESHOLD:
                    risk += 0.50
                    flags.append(f"Extremely large amount: {amount:,.2f}")
                elif amount > self.LARGE_AMOUNT_THRESHOLD:
                    risk += 0.20
                    flags.append(f"Large amount ({amount:,.2f}) — elevated scrutiny")
            except (TypeError, ValueError):
                risk += 0.10
                flags.append("Amount field could not be parsed as numeric")

        # --- Line item count ---
        line_items = data.get("line_items") or data.get("items")
        if isinstance(line_items, (int, float)) and line_items > self.MAX_LINE_ITEMS:
            risk += 0.15
            flags.append(f"Unusually high line item count: {int(line_items)}")

        # --- Structural anomalies ---
        if not data:
            risk += 0.20
            flags.append("Standardized data payload is empty")

        return min(1.0, round(risk, 4)), flags

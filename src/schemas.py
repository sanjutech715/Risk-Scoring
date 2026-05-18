"""
Pydantic schemas — request and response models for the scoring API.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, List, Optional
from enum import Enum


class Recommendation(str, Enum):
    APPROVE = "approve"
    REVIEW = "review"
    REJECT = "reject"


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    field_coverage: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ScoringRequest(BaseModel):
    document_id: str = Field(..., min_length=1, max_length=128, description="Unique document identifier")
    standardized_data: Dict[str, Any] = Field(..., description="Normalized document fields")
    validation_result: ValidationResult = Field(..., description="Pre-validated document state")
    classification_confidence: float = Field(..., ge=0.0, le=1.0, description="Upstream classifier confidence")

    model_config = {
        "json_schema_extra": {
            "example": {
                "document_id": "DOC001",
                "standardized_data": {
                    "type": "invoice",
                    "amount": 1250.00,
                    "currency": "USD",
                    "vendor": "Acme Corp",
                    "date": "2025-03-15",
                    "line_items": 3
                },
                "validation_result": {
                    "is_valid": True,
                    "errors": [],
                    "warnings": [],
                    "field_coverage": 0.95
                },
                "classification_confidence": 0.94
            }
        }
    }


class RiskBreakdown(BaseModel):
    validation_risk: float = Field(..., ge=0.0, le=1.0, description="Risk from validation errors/warnings")
    confidence_risk: float = Field(..., ge=0.0, le=1.0, description="Risk from low classifier confidence")
    data_completeness_risk: float = Field(..., ge=0.0, le=1.0, description="Risk from missing or sparse data")
    anomaly_risk: float = Field(..., ge=0.0, le=1.0, description="Risk from detected anomalies")


class ScoringResponse(BaseModel):
    document_id: str
    summary: str = Field(..., description="Natural-language document summary")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Composite risk score (0=safe, 1=high-risk)")
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Pipeline confidence in this result")
    recommendation: Recommendation
    risk_breakdown: RiskBreakdown
    flags: List[str] = Field(default_factory=list, description="Human-readable risk flags")
    processed_at: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "document_id": "DOC001",
                "summary": "Invoice processed successfully",
                "risk_score": 0.12,
                "overall_confidence": 0.95,
                "recommendation": "approve",
                "risk_breakdown": {
                    "validation_risk": 0.0,
                    "confidence_risk": 0.06,
                    "data_completeness_risk": 0.05,
                    "anomaly_risk": 0.01
                },
                "flags": [],
                "processed_at": "2025-03-15T12:00:00Z"
            }
        }
    }


class BatchScoringRequest(BaseModel):
    documents: List[ScoringRequest] = Field(..., min_length=1, max_length=50)


class BatchSummary(BaseModel):
    total: int
    approved: int
    review: int
    rejected: int
    avg_risk_score: float
    avg_confidence: float


class BatchScoringResponse(BaseModel):
    results: List[ScoringResponse]
    batch_summary: BatchSummary


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    models_loaded: bool

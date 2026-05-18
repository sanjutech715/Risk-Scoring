"""
Summary & Risk Scoring API
Document processing pipeline module: generates summaries, confidence scores, and risk-based recommendations.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
import uvicorn
import logging
from datetime import datetime

from .schemas import ScoringRequest, ScoringResponse, HealthResponse, BatchScoringRequest, BatchScoringResponse
from .scoring_service import ScoringService
from .logger import setup_logger

logger = setup_logger(__name__)

app = FastAPI(
    title="Summary & Risk Scoring API",
    description="Intelligent document scoring pipeline — generates summaries, confidence scores, and risk-based recommendations.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

scoring_service = ScoringService()


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """System health and readiness check."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        models_loaded=scoring_service.is_ready()
    )


@app.post("/api/v1/score", response_model=ScoringResponse, tags=["Scoring"])
async def score_document(request: ScoringRequest):
    """
    Core scoring endpoint.

    Accepts a validated document payload and returns:
    - A natural-language summary
    - A risk score (0.0 → 1.0, lower = safer)
    - An overall confidence score
    - A recommendation: approve | review | reject

    Example input:
    ```json
    {
      "document_id": "DOC001",
      "standardized_data": { "type": "invoice", "amount": 1250.00, "vendor": "Acme Corp" },
      "validation_result": { "is_valid": true, "errors": [] },
      "classification_confidence": 0.94
    }
    ```
    """
    try:
        logger.info(f"Scoring request received for document: {request.document_id}")
        result = await scoring_service.score(request)
        logger.info(f"Scoring complete for {request.document_id} → {result.recommendation} (risk={result.risk_score:.3f})")
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Scoring failed for {request.document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal scoring error")


@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html>
      <head><title>Summary & Risk Scoring API</title></head>
      <body>
        <h1>Summary & Risk Scoring API</h1>
        <p>API is running.</p>
        <ul>
          <li><a href=\"/docs\">OpenAPI docs</a></li>
          <li><a href=\"/health\">Health endpoint</a></li>
        </ul>
      </body>
    </html>
    """


@app.post("/api/v1/score/batch", response_model=BatchScoringResponse, tags=["Scoring"])
async def score_documents_batch(request: BatchScoringRequest, background_tasks: BackgroundTasks):
    """
    Batch scoring endpoint — process up to 50 documents in a single call.
    Returns individual results with a batch-level summary.
    """
    if len(request.documents) > 50:
        raise HTTPException(status_code=400, detail="Batch size limit is 50 documents.")
    try:
        logger.info(f"Batch scoring {len(request.documents)} documents")
        results = await scoring_service.score_batch(request.documents)
        return results
    except Exception as e:
        logger.error(f"Batch scoring failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Batch scoring error")


@app.get("/api/v1/thresholds", tags=["Configuration"])
async def get_thresholds():
    """Return current risk and confidence threshold configuration."""
    return scoring_service.get_thresholds()


@app.get("/api/v1/metrics", tags=["Observability"])
async def get_metrics():
    """
    Return live scoring metrics snapshot.

    Includes:
    - total_scored: total documents processed
    - recommendation_distribution: approve/review/reject counts
    - avg_latency_ms / max_latency_ms: scoring performance
    - top_flags: most frequent risk flag categories
    """
    return scoring_service.get_metrics()


#if __name__ == "__main__":
 #   uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
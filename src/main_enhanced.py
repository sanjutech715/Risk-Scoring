"""
Enhanced Summary & Risk Scoring API

Extended features:
  - File upload endpoints (JSON, CSV)
  - Batch processing with file I/O
  - Export results in multiple formats
  - WebSocket support for real-time processing
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
import uvicorn
import logging
import tempfile
import io
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from .schemas import (
    ScoringRequest, ScoringResponse, HealthResponse, 
    BatchScoringRequest, BatchScoringResponse
)
from .scoring_service import ScoringService
from .io_handler import IOProcessor, InputFormat, OutputFormat
from .logger import setup_logger

logger = setup_logger(__name__)

app = FastAPI(
    title="Summary & Risk Scoring API - Enhanced",
    description="Intelligent document scoring pipeline with file upload and multiple output formats.",
    version="2.0.0",
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
io_processor = IOProcessor()


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """System health and readiness check."""
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        timestamp=datetime.utcnow().isoformat(),
        models_loaded=scoring_service.is_ready()
    )


@app.post("/api/v1/score", response_model=ScoringResponse, tags=["Scoring"])
async def score_document(request: ScoringRequest):
    """
    Core scoring endpoint - processes a single document.
    
    Returns risk score, confidence, recommendation, and summary.
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


@app.post("/api/v1/score/batch", response_model=BatchScoringResponse, tags=["Scoring"])
async def score_documents_batch(request: BatchScoringRequest, background_tasks: BackgroundTasks):
    """
    Batch scoring endpoint — process up to 50 documents in a single call.
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


@app.post("/api/v2/upload/json", tags=["File Upload"])
async def upload_json_file(
    file: UploadFile = File(...),
    output_format: str = Query("json", pattern="^(json|csv)$")
):
    """
    Upload and process a JSON file containing one or more documents.
    
    Returns processed results in specified format.
    """
    try:
        # Read uploaded file
        content = await file.read()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.json') as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        # Load and process
        requests = io_processor.load_input(tmp_path, format=InputFormat.JSON)
        logger.info(f"Processing {len(requests)} documents from uploaded JSON")
        
        if len(requests) == 1:
            result = await scoring_service.score(requests[0])
            results = [result]
        else:
            batch_response = await scoring_service.score_batch(requests)
            results = batch_response.results
        
        # Clean up temp file
        Path(tmp_path).unlink()
        
        # Return in requested format
        if output_format == "csv":
            # Create CSV in memory
            output = io.StringIO()
            import csv
            
            fieldnames = [
                "document_id", "recommendation", "risk_score", "overall_confidence",
                "validation_risk", "confidence_risk", "data_completeness_risk", 
                "anomaly_risk", "summary"
            ]
            
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                writer.writerow({
                    "document_id": result.document_id,
                    "recommendation": result.recommendation.value,
                    "risk_score": result.risk_score,
                    "overall_confidence": result.overall_confidence,
                    "validation_risk": result.risk_breakdown.validation_risk,
                    "confidence_risk": result.risk_breakdown.confidence_risk,
                    "data_completeness_risk": result.risk_breakdown.data_completeness_risk,
                    "anomaly_risk": result.risk_breakdown.anomaly_risk,
                    "summary": result.summary,
                })
            
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=results.csv"}
            )
        else:
            # Return JSON
            return {"results": [r.model_dump() for r in results]}
            
    except Exception as e:
        logger.error(f"File upload processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/upload/csv", tags=["File Upload"])
async def upload_csv_file(
    file: UploadFile = File(...),
    output_format: str = Query("json", pattern="^(json|csv)$")
):
    """
    Upload and process a CSV file containing multiple documents.
    
    Expected CSV columns:
    - document_id, type, amount, vendor, date, currency, line_items
    - is_valid, errors, warnings, field_coverage, classification_confidence
    """
    try:
        # Read uploaded file
        content = await file.read()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.csv') as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        # Load and process
        requests = io_processor.load_input(tmp_path, format=InputFormat.CSV)
        logger.info(f"Processing {len(requests)} documents from uploaded CSV")
        
        batch_response = await scoring_service.score_batch(requests)
        results = batch_response.results
        
        # Clean up temp file
        Path(tmp_path).unlink()
        
        # Return in requested format
        if output_format == "csv":
            # Create CSV response
            output = io.StringIO()
            import csv
            
            fieldnames = [
                "document_id", "recommendation", "risk_score", "overall_confidence",
                "flags", "summary"
            ]
            
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                writer.writerow({
                    "document_id": result.document_id,
                    "recommendation": result.recommendation.value,
                    "risk_score": result.risk_score,
                    "overall_confidence": result.overall_confidence,
                    "flags": " | ".join(result.flags),
                    "summary": result.summary,
                })
            
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=results.csv"}
            )
        else:
            # Return JSON with batch summary
            return {
                "results": [r.model_dump() for r in results],
                "batch_summary": batch_response.batch_summary.model_dump()
            }
            
    except Exception as e:
        logger.error(f"CSV upload processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/thresholds", tags=["Configuration"])
async def get_thresholds():
    """Return current risk and confidence threshold configuration."""
    return scoring_service.get_thresholds()


@app.get("/api/v2/export/template/csv", tags=["Templates"])
async def download_csv_template():
    """Download a CSV template for batch uploads."""
    template = """document_id,type,amount,vendor,date,currency,line_items,is_valid,errors,warnings,field_coverage,classification_confidence
DOC-001,invoice,1250.50,Acme Corp,2025-03-15,USD,5,true,,,0.95,0.94
DOC-002,receipt,125.99,Coffee Shop,2025-04-01,USD,1,true,,,0.85,0.88"""
    
    return StreamingResponse(
        iter([template]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=template.csv"}
    )


@app.get("/api/v2/stats", tags=["Analytics"])
async def get_processing_stats():
    """Get processing statistics (placeholder for future enhancement)."""
    return {
        "total_processed": 0,
        "today_processed": 0,
        "avg_processing_time_ms": 0,
        "thresholds": scoring_service.get_thresholds()
    }


if __name__ == "__main__":
    uvicorn.run("main_enhanced:app", host="0.0.0.0", port=8000, reload=True)

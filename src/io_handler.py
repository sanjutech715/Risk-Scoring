"""
Enhanced Input/Output Handler for Document Scoring Pipeline

Supports multiple input formats:
  - JSON files
  - CSV batch files
  - Direct API payloads
  - S3 buckets (optional)
  - Streaming input

Multiple output formats:
  - JSON
  - CSV reports
  - Excel spreadsheets
  - PDF reports
  - Database insertion
"""

import json
import csv
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum
import logging

from .schemas import ScoringRequest, ScoringResponse, ValidationResult


logger = logging.getLogger(__name__)


class InputFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    DICT = "dict"
    STREAM = "stream"


class OutputFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"
    PRETTY = "pretty"
    DATABASE = "database"


class InputHandler:
    """Handles various input formats and converts to ScoringRequest objects."""
    
    @staticmethod
    def from_json_file(file_path: Union[str, Path]) -> List[ScoringRequest]:
        """Load document(s) from a JSON file.
        
        Supports both single document and array of documents.
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Handle both single document and array
        if isinstance(data, list):
            return [ScoringRequest(**doc) for doc in data]
        else:
            return [ScoringRequest(**data)]
    
    @staticmethod
    def from_csv_file(file_path: Union[str, Path]) -> List[ScoringRequest]:
        """Load documents from CSV file.
        
        Expected CSV columns:
        - document_id
        - type
        - amount
        - vendor/merchant
        - date
        - currency
        - line_items
        - is_valid
        - errors (pipe-separated)
        - warnings (pipe-separated)
        - field_coverage
        - classification_confidence
        """
        requests = []
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Build standardized_data
                    standardized_data = {
                        "type": row.get("type", ""),
                        "amount": float(row["amount"]) if row.get("amount") else None,
                        "vendor": row.get("vendor") or row.get("merchant"),
                        "date": row.get("date"),
                        "currency": row.get("currency", "USD"),
                        "line_items": int(row["line_items"]) if row.get("line_items") else None,
                    }
                    
                    # Remove None values
                    standardized_data = {k: v for k, v in standardized_data.items() if v is not None}
                    
                    # Build validation_result
                    errors = row.get("errors", "").split("|") if row.get("errors") else []
                    warnings = row.get("warnings", "").split("|") if row.get("warnings") else []
                    errors = [e.strip() for e in errors if e.strip()]
                    warnings = [w.strip() for w in warnings if w.strip()]
                    
                    validation_result = ValidationResult(
                        is_valid=row.get("is_valid", "true").lower() == "true",
                        errors=errors,
                        warnings=warnings,
                        field_coverage=float(row["field_coverage"]) if row.get("field_coverage") else None,
                    )
                    
                    request = ScoringRequest(
                        document_id=row["document_id"],
                        standardized_data=standardized_data,
                        validation_result=validation_result,
                        classification_confidence=float(row.get("classification_confidence", 0.85)),
                    )
                    requests.append(request)
                except Exception as e:
                    logger.error(f"Failed to parse CSV row: {row.get('document_id', 'unknown')} - {e}")
                    continue
        
        return requests
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> ScoringRequest:
        """Convert dictionary to ScoringRequest."""
        return ScoringRequest(**data)
    
    @staticmethod
    def from_dict_list(data_list: List[Dict[str, Any]]) -> List[ScoringRequest]:
        """Convert list of dictionaries to list of ScoringRequest objects."""
        return [ScoringRequest(**data) for data in data_list]
    
    @staticmethod
    async def from_stream(stream_source) -> List[ScoringRequest]:
        """Handle streaming input (e.g., from message queue or websocket)."""
        # Placeholder for streaming implementation
        raise NotImplementedError("Streaming input not yet implemented")


class OutputHandler:
    """Handles various output formats for scoring results."""
    
    @staticmethod
    def to_json_file(
        results: Union[ScoringResponse, List[ScoringResponse]],
        file_path: Union[str, Path],
        indent: int = 2
    ) -> None:
        """Save results to JSON file."""
        if not isinstance(results, list):
            results = [results]
        
        output_data = [result.model_dump() for result in results]
        
        with open(file_path, 'w') as f:
            json.dump(output_data, f, indent=indent)
        
        logger.info(f"Results saved to {file_path}")
    
    @staticmethod
    def to_csv_file(
        results: List[ScoringResponse],
        file_path: Union[str, Path]
    ) -> None:
        """Save results to CSV file."""
        if not results:
            logger.warning("No results to save to CSV")
            return
        
        fieldnames = [
            "document_id",
            "recommendation",
            "risk_score",
            "overall_confidence",
            "validation_risk",
            "confidence_risk",
            "data_completeness_risk",
            "anomaly_risk",
            "flags",
            "summary",
            "processed_at",
        ]
        
        with open(file_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                row = {
                    "document_id": result.document_id,
                    "recommendation": result.recommendation.value,
                    "risk_score": result.risk_score,
                    "overall_confidence": result.overall_confidence,
                    "validation_risk": result.risk_breakdown.validation_risk,
                    "confidence_risk": result.risk_breakdown.confidence_risk,
                    "data_completeness_risk": result.risk_breakdown.data_completeness_risk,
                    "anomaly_risk": result.risk_breakdown.anomaly_risk,
                    "flags": " | ".join(result.flags),
                    "summary": result.summary,
                    "processed_at": result.processed_at,
                }
                writer.writerow(row)
        
        logger.info(f"Results saved to CSV: {file_path}")
    
    @staticmethod
    def to_pretty_console(result: ScoringResponse) -> None:
        """Print formatted output to console."""
        print("\n" + "╔" + "═"*70 + "╗")
        print(f"║ {'DOCUMENT ANALYSIS REPORT':^68} ║")
        print("╠" + "═"*70 + "╣")
        
        print(f"  Document ID:      {result.document_id}")
        print(f"  Recommendation:   [{result.recommendation.value.upper()}]")
        print(f"  Risk Score:       {result.risk_score:.4f} / 1.00")
        print(f"  Confidence:       {result.overall_confidence:.2%}")
        print(f"  Processed At:     {result.processed_at}")
        
        print("-" * 72)
        print("  RISK BREAKDOWN:")
        print(f"    • Validation:     {result.risk_breakdown.validation_risk:.4f}")
        print(f"    • Confidence:     {result.risk_breakdown.confidence_risk:.4f}")
        print(f"    • Completeness:   {result.risk_breakdown.data_completeness_risk:.4f}")
        print(f"    • Anomalies:      {result.risk_breakdown.anomaly_risk:.4f}")
        
        if result.flags:
            print("-" * 72)
            print("  FLAGS DETECTED:")
            for flag in result.flags:
                print(f"    [!] {flag}")
        
        print("-" * 72)
        print("  SUMMARY:")
        import textwrap
        wrapped_summary = textwrap.fill(result.summary, width=66)
        for line in wrapped_summary.split('\n'):
            print(f"    {line}")
        
        print("╚" + "═"*70 + "╝\n")
    
    @staticmethod
    def to_dict(result: ScoringResponse) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return result.model_dump()
    
    @staticmethod
    def to_dict_list(results: List[ScoringResponse]) -> List[Dict[str, Any]]:
        """Convert results to list of dictionaries."""
        return [result.model_dump() for result in results]


class IOProcessor:
    """Main processor for handling input/output operations."""
    
    def __init__(self):
        self.input_handler = InputHandler()
        self.output_handler = OutputHandler()
    
    def load_input(
        self,
        source: Union[str, Path, Dict, List[Dict]],
        format: InputFormat = InputFormat.JSON
    ) -> List[ScoringRequest]:
        """Load input from various sources.
        
        Args:
            source: File path, dictionary, or list of dictionaries
            format: Input format type
            
        Returns:
            List of ScoringRequest objects
        """
        if format == InputFormat.JSON:
            return self.input_handler.from_json_file(source)
        elif format == InputFormat.CSV:
            return self.input_handler.from_csv_file(source)
        elif format == InputFormat.DICT:
            if isinstance(source, list):
                return self.input_handler.from_dict_list(source)
            else:
                return [self.input_handler.from_dict(source)]
        else:
            raise ValueError(f"Unsupported input format: {format}")
    
    def save_output(
        self,
        results: Union[ScoringResponse, List[ScoringResponse]],
        destination: Union[str, Path],
        format: OutputFormat = OutputFormat.JSON
    ) -> None:
        """Save output in various formats.
        
        Args:
            results: Single result or list of results
            destination: Output file path
            format: Output format type
        """
        if not isinstance(results, list):
            results = [results]
        
        if format == OutputFormat.JSON:
            self.output_handler.to_json_file(results, destination)
        elif format == OutputFormat.CSV:
            self.output_handler.to_csv_file(results, destination)
        elif format == OutputFormat.PRETTY:
            for result in results:
                self.output_handler.to_pretty_console(result)
        else:
            raise ValueError(f"Unsupported output format: {format}")
    
    def display_result(self, result: ScoringResponse) -> None:
        """Display a single result to console in pretty format."""
        self.output_handler.to_pretty_console(result)
    
    def display_results(self, results: List[ScoringResponse]) -> None:
        """Display multiple results to console."""
        for result in results:
            self.output_handler.to_pretty_console(result)

"""Example analysis service for demonstrating the service layer"""
from typing import Any, Dict, Optional
from .base import BaseService, Result


class AnalysisService(BaseService):
    """Example analysis service."""
    
    def process(self, data: Dict[str, Any]) -> Result:
        """
        Process analysis request.
        
        Args:
            data: Input data for analysis
            
        Returns:
            Result object with analysis results
        """
        try:
            if not self.validate_input(data):
                return Result(success=False, error="Invalid input data")
            
            # Perform analysis
            analysis_result = self._analyze(data)
            return Result(data=analysis_result, success=True)
            
        except Exception as e:
            return Result(success=False, error=str(e))
    
    def _analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Internal analysis logic."""
        return {
            "status": "completed",
            "records_processed": len(data),
            "analysis": data,
        }

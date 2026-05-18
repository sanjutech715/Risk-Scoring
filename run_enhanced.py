"""
Enhanced Document Scoring Runner

Supports multiple input/output formats and batch processing modes.

Usage examples:
    # Single JSON file
    python run_enhanced.py --input act.json --output results.json
    
    # CSV batch processing
    python run_enhanced.py --input batch.csv --output results.csv --format csv
    
    # Multiple files
    python run_enhanced.py --input doc1.json doc2.json doc3.json --output batch_results.json
    
    # Pretty console output
    python run_enhanced.py --input act.json --format pretty
    
    # All output formats
    python run_enhanced.py --input act.json --output-json results.json --output-csv results.csv
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Optional

from src.schemas import ScoringRequest
from src.scoring_service import ScoringService
from src.io_handler import IOProcessor, InputFormat, OutputFormat
from src.logger import setup_logger

logger = setup_logger(__name__)


class DocumentProcessor:
    """Enhanced document processor with flexible I/O."""
    
    def __init__(self):
        self.scoring_service = ScoringService()
        self.io_processor = IOProcessor()
    
    async def process_single(self, request: ScoringRequest, verbose: bool = False):
        """Process a single document."""
        logger.info(f"Processing document: {request.document_id}")
        result = await self.scoring_service.score(request)
        
        if verbose:
            self.io_processor.display_result(result)
        
        return result
    
    async def process_batch(self, requests: List[ScoringRequest], verbose: bool = False):
        """Process multiple documents."""
        logger.info(f"Processing batch of {len(requests)} documents")
        batch_response = await self.scoring_service.score_batch(requests)
        
        if verbose:
            print("\n" + "="*72)
            print(f"BATCH SUMMARY: {len(requests)} documents processed")
            print("="*72)
            print(f"  Approved:  {batch_response.batch_summary.approved}")
            print(f"  Review:    {batch_response.batch_summary.review}")
            print(f"  Rejected:  {batch_response.batch_summary.rejected}")
            print(f"  Avg Risk:  {batch_response.batch_summary.avg_risk_score:.4f}")
            print(f"  Avg Conf:  {batch_response.batch_summary.avg_confidence:.2%}")
            print("="*72 + "\n")
        
        return batch_response.results
    
    async def process_from_file(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        input_format: InputFormat = InputFormat.JSON,
        output_format: OutputFormat = OutputFormat.JSON,
        verbose: bool = True
    ):
        """Process documents from file."""
        # Load input
        logger.info(f"Loading input from: {input_path}")
        requests = self.io_processor.load_input(input_path, format=input_format)
        logger.info(f"Loaded {len(requests)} document(s)")
        
        # Process
        if len(requests) == 1:
            results = [await self.process_single(requests[0], verbose=verbose)]
        else:
            results = await self.process_batch(requests, verbose=verbose)
        
        # Save output
        if output_path:
            logger.info(f"Saving results to: {output_path}")
            self.io_processor.save_output(results, output_path, format=output_format)
        elif verbose and output_format != OutputFormat.PRETTY:
            # Display to console if no output file specified
            self.io_processor.display_results(results)
        
        return results
    
    async def process_multiple_files(
        self,
        input_paths: List[str],
        output_path: Optional[str] = None,
        output_format: OutputFormat = OutputFormat.JSON,
        verbose: bool = True
    ):
        """Process multiple input files and combine results."""
        all_results = []
        
        for input_path in input_paths:
            logger.info(f"Processing file: {input_path}")
            requests = self.io_processor.load_input(input_path, format=InputFormat.JSON)
            
            for request in requests:
                result = await self.process_single(request, verbose=False)
                all_results.append(result)
        
        if verbose:
            print(f"\n{'='*72}")
            print(f"TOTAL PROCESSED: {len(all_results)} documents from {len(input_paths)} files")
            print(f"{'='*72}\n")
        
        # Save combined output
        if output_path:
            self.io_processor.save_output(all_results, output_path, format=output_format)
        elif verbose:
            self.io_processor.display_results(all_results)
        
        return all_results


async def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Enhanced Document Scoring Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input act.json
  %(prog)s --input batch.csv --output results.csv --format csv
  %(prog)s --input doc1.json doc2.json --output combined.json
  %(prog)s --input act.json --output-json results.json --output-csv report.csv
        """
    )
    
    # Input options
    parser.add_argument(
        '--input', '-i',
        nargs='+',
        required=True,
        help='Input file(s) to process'
    )
    parser.add_argument(
        '--input-format',
        choices=['json', 'csv'],
        default='json',
        help='Input file format (default: json)'
    )
    
    # Output options
    parser.add_argument(
        '--output', '-o',
        help='Output file path'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['json', 'csv', 'pretty'],
        default='json',
        help='Output format (default: json)'
    )
    
    # Multiple output formats
    parser.add_argument(
        '--output-json',
        help='Save results as JSON to specified path'
    )
    parser.add_argument(
        '--output-csv',
        help='Save results as CSV to specified path'
    )
    
    # Display options
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress console output'
    )
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = DocumentProcessor()
    
    # Auto-detect input format based on file extensions
    input_extensions = {Path(f).suffix.lower() for f in args.input}
    if '.csv' in input_extensions:
        input_format = InputFormat.CSV
    elif '.json' in input_extensions:
        input_format = InputFormat.JSON
    else:
        input_format = InputFormat.JSON  # default
    
    output_format = {
        'json': OutputFormat.JSON,
        'csv': OutputFormat.CSV,
        'pretty': OutputFormat.PRETTY
    }[args.format]
    
    verbose = args.verbose and not args.quiet
    
    try:
        # Process input files
        if len(args.input) == 1:
            # Single file
            results = await processor.process_from_file(
                args.input[0],
                args.output,
                input_format=input_format,
                output_format=output_format,
                verbose=verbose
            )
        else:
            # Multiple files
            results = await processor.process_multiple_files(
                args.input,
                args.output,
                output_format=output_format,
                verbose=verbose
            )
        
        # Save to additional output formats if specified
        if args.output_json and args.output_json != args.output:
            processor.io_processor.save_output(results, args.output_json, OutputFormat.JSON)
        
        if args.output_csv and args.output_csv != args.output:
            processor.io_processor.save_output(results, args.output_csv, OutputFormat.CSV)
        
        logger.info("Processing completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        return 1


async def process_document_simple(input_file: str = "data/act.json"):
    """Simple function for programmatic use - processes a single document."""
    processor = DocumentProcessor()
    results = await processor.process_from_file(
        input_file,
        output_path=None,
        verbose=True
    )
    return results[0] if results else None


if __name__ == "__main__":
    # If called with no arguments, run simple mode with act.json
    if len(sys.argv) == 1:
        print("Running in simple mode with data/act.json...")
        print("For more options, use: python run_enhanced.py --help\n")
        exit_code = asyncio.run(process_document_simple())
        sys.exit(0 if exit_code else 1)
    else:
        # Run with CLI arguments
        exit_code = asyncio.run(main())
        sys.exit(exit_code)

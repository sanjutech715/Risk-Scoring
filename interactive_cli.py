"""
Interactive Document Scoring CLI

Provides an easy-to-use command-line interface for document processing
with menu-driven options and guided workflows.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

from src.schemas import ScoringRequest, ValidationResult
from src.scoring_service import ScoringService
from src.io_handler import IOProcessor, InputFormat, OutputFormat
from src.logger import setup_logger

logger = setup_logger(__name__)


class InteractiveCLI:
    """Interactive command-line interface for document scoring."""
    
    def __init__(self):
        self.scoring_service = ScoringService()
        self.io_processor = IOProcessor()
    
    def display_header(self):
        """Display application header."""
        print("\n" + "="*72)
        print(" "*20 + "DOCUMENT SCORING SYSTEM")
        print(" "*25 + "Version 2.0")
        print("="*72 + "\n")
    
    def display_menu(self):
        """Display main menu options."""
        print("\nMAIN MENU:")
        print("  1. Process single JSON file")
        print("  2. Process CSV batch file")
        print("  3. Process multiple JSON files")
        print("  4. Manual document entry")
        print("  5. View sample data")
        print("  6. Export results")
        print("  7. View configuration")
        print("  8. Exit")
        print()
    
    def get_user_choice(self, prompt: str, valid_choices: list) -> str:
        """Get validated user input."""
        while True:
            choice = input(prompt).strip()
            if choice in valid_choices:
                return choice
            print(f"Invalid choice. Please select from: {', '.join(valid_choices)}")
    
    async def process_json_file(self):
        """Process a single JSON file."""
        file_path = input("\nEnter JSON file path (or press Enter for 'data/act.json'): ").strip()
        if not file_path:
            file_path = "data/act.json"
        
        if not Path(file_path).exists():
            print(f"Error: File '{file_path}' not found.")
            return
        
        try:
            print(f"\nProcessing {file_path}...")
            requests = self.io_processor.load_input(file_path, format=InputFormat.JSON)
            
            for request in requests:
                result = await self.scoring_service.score(request)
                self.io_processor.display_result(result)
            
            # Ask to save
            save = self.get_user_choice("\nSave results? (y/n): ", ['y', 'n', 'Y', 'N'])
            if save.lower() == 'y':
                output_path = input("Enter output file path: ").strip()
                output_format = self.get_user_choice(
                    "Select format (json/csv): ", 
                    ['json', 'csv']
                )
                
                results = []
                for request in requests:
                    result = await self.scoring_service.score(request)
                    results.append(result)
                
                fmt = OutputFormat.JSON if output_format == 'json' else OutputFormat.CSV
                self.io_processor.save_output(results, output_path, format=fmt)
                print(f"\n✓ Results saved to {output_path}")
        
        except Exception as e:
            print(f"\n✗ Error processing file: {e}")
    
    async def process_csv_batch(self):
        """Process CSV batch file."""
        file_path = input("\nEnter CSV file path (or press Enter for 'batch_input.csv'): ").strip()
        if not file_path:
            file_path = "batch_input.csv"
        
        if not Path(file_path).exists():
            print(f"Error: File '{file_path}' not found.")
            return
        
        try:
            print(f"\nProcessing {file_path}...")
            requests = self.io_processor.load_input(file_path, format=InputFormat.CSV)
            print(f"Loaded {len(requests)} documents")
            
            batch_response = await self.scoring_service.score_batch(requests)
            
            # Display summary
            print("\n" + "="*72)
            print("BATCH PROCESSING SUMMARY")
            print("="*72)
            print(f"  Total Documents:  {batch_response.batch_summary.total}")
            print(f"  Approved:         {batch_response.batch_summary.approved}")
            print(f"  Review Required:  {batch_response.batch_summary.review}")
            print(f"  Rejected:         {batch_response.batch_summary.rejected}")
            print(f"  Avg Risk Score:   {batch_response.batch_summary.avg_risk_score:.4f}")
            print(f"  Avg Confidence:   {batch_response.batch_summary.avg_confidence:.2%}")
            print("="*72)
            
            # Show details option
            show_details = self.get_user_choice("\nShow individual results? (y/n): ", ['y', 'n', 'Y', 'N'])
            if show_details.lower() == 'y':
                for result in batch_response.results:
                    self.io_processor.display_result(result)
            
            # Save option
            save = self.get_user_choice("\nSave results? (y/n): ", ['y', 'n', 'Y', 'N'])
            if save.lower() == 'y':
                output_path = input("Enter output file path: ").strip()
                output_format = self.get_user_choice("Select format (json/csv): ", ['json', 'csv'])
                
                fmt = OutputFormat.JSON if output_format == 'json' else OutputFormat.CSV
                self.io_processor.save_output(batch_response.results, output_path, format=fmt)
                print(f"\n✓ Results saved to {output_path}")
        
        except Exception as e:
            print(f"\n✗ Error processing file: {e}")
    
    async def manual_entry(self):
        """Manual document entry."""
        print("\n" + "="*72)
        print("MANUAL DOCUMENT ENTRY")
        print("="*72)
        
        doc_id = input("\nDocument ID: ").strip()
        doc_type = input("Document Type (invoice/receipt/contract/claim): ").strip() or "invoice"
        
        amount_str = input("Amount: ").strip()
        try:
            amount = float(amount_str) if amount_str else 1000.0
        except ValueError:
            amount = 1000.0
            print(f"Invalid amount, using default: {amount}")
        
        vendor = input("Vendor/Merchant: ").strip() or "Unknown Vendor"
        date = input("Date (YYYY-MM-DD): ").strip() or "2025-04-01"
        currency = input("Currency (USD/EUR/GBP): ").strip() or "USD"
        
        line_items_str = input("Number of line items: ").strip()
        try:
            line_items = int(line_items_str) if line_items_str else 1
        except ValueError:
            line_items = 1
        
        is_valid = self.get_user_choice("Is document valid? (y/n): ", ['y', 'n', 'Y', 'N']).lower() == 'y'
        
        confidence_str = input("Classification confidence (0.0-1.0): ").strip()
        try:
            confidence = float(confidence_str) if confidence_str else 0.85
            confidence = max(0.0, min(1.0, confidence))
        except ValueError:
            confidence = 0.85
        
        # Build request
        request = ScoringRequest(
            document_id=doc_id,
            standardized_data={
                "type": doc_type,
                "amount": amount,
                "vendor": vendor,
                "date": date,
                "currency": currency,
                "line_items": line_items,
            },
            validation_result=ValidationResult(
                is_valid=is_valid,
                errors=[],
                warnings=[],
                field_coverage=0.90,
            ),
            classification_confidence=confidence,
        )
        
        print("\nProcessing...")
        result = await self.scoring_service.score(request)
        self.io_processor.display_result(result)
        
        # Save option
        save = self.get_user_choice("\nSave result? (y/n): ", ['y', 'n', 'Y', 'N'])
        if save.lower() == 'y':
            output_path = input("Enter output file path: ").strip()
            self.io_processor.save_output([result], output_path, format=OutputFormat.JSON)
            print(f"\n✓ Result saved to {output_path}")
    
    def view_sample_data(self):
        """Display sample input data."""
        print("\n" + "="*72)
        print("SAMPLE JSON INPUT FORMAT")
        print("="*72)
        sample = '''{
  "document_id": "DOC-001",
  "standardized_data": {
    "type": "invoice",
    "amount": 1250.50,
    "vendor": "Acme Corp",
    "date": "2025-03-15",
    "currency": "USD",
    "line_items": 5
  },
  "validation_result": {
    "is_valid": true,
    "errors": [],
    "warnings": [],
    "field_coverage": 0.95
  },
  "classification_confidence": 0.94
}'''
        print(sample)
        print("="*72)
    
    def view_configuration(self):
        """Display current configuration."""
        print("\n" + "="*72)
        print("CURRENT CONFIGURATION")
        print("="*72)
        
        thresholds = self.scoring_service.get_thresholds()
        
        print("\nThresholds:")
        print(f"  Approve (max risk):     {thresholds['approve_max_risk']}")
        print(f"  Review (max risk):      {thresholds['review_max_risk']}")
        print(f"  Min confidence:         {thresholds['min_confidence_for_approve']}")
        
        print("\nScorer Weights:")
        for name, weight in thresholds['weights'].items():
            print(f"  {name:20s}: {weight:.2f}")
        
        print("="*72)
    
    async def run(self):
        """Main application loop."""
        self.display_header()
        
        while True:
            self.display_menu()
            choice = self.get_user_choice("Select option (1-8): ", 
                                         ['1', '2', '3', '4', '5', '6', '7', '8'])
            
            if choice == '1':
                await self.process_json_file()
            elif choice == '2':
                await self.process_csv_batch()
            elif choice == '3':
                print("\nMultiple files not yet implemented in interactive mode.")
                print("Use: python run_enhanced.py --input file1.json file2.json")
            elif choice == '4':
                await self.manual_entry()
            elif choice == '5':
                self.view_sample_data()
            elif choice == '6':
                print("\nExport functionality available after processing documents.")
            elif choice == '7':
                self.view_configuration()
            elif choice == '8':
                print("\nGoodbye!")
                break
            
            input("\nPress Enter to continue...")


async def main():
    """Entry point."""
    cli = InteractiveCLI()
    await cli.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
        sys.exit(0)

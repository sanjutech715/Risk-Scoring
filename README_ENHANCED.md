# Enhanced Summary & Risk Scoring API - Version 2.0

Intelligent document scoring pipeline with **flexible input/output**, **batch processing**, and **multiple export formats**.

---

## 🆕 What's New in Version 2.0

### Enhanced Input/Output System
- ✅ **Multiple Input Formats**: JSON, CSV, batch files
- ✅ **Multiple Output Formats**: JSON, CSV, Pretty Console, Excel (planned)
- ✅ **File Upload API**: Direct file upload endpoints
- ✅ **Interactive CLI**: Menu-driven interface for easy use
- ✅ **Batch Processing**: Process hundreds of documents efficiently
- ✅ **Command-line Tool**: Powerful CLI with multiple options

### New Components
- `io_handler.py` - Flexible input/output processing
- `run_enhanced.py` - Enhanced runner with CLI arguments
- `interactive_cli.py` - User-friendly interactive interface
- `main_enhanced.py` - Extended FastAPI with file upload
- `batch_input.csv` - Sample CSV batch file

---

## 🚀 Quick Start

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Run with Different Methods

#### Method A: Interactive CLI (Easiest)
```bash
python interactive_cli.py
```
- Menu-driven interface
- Guided workflows
- Perfect for beginners

#### Method B: Command Line (Most Flexible)
```bash
# Single file
python run_enhanced.py --input act.json

# CSV batch
python run_enhanced.py --input batch_input.csv --format csv

# Multiple files
python run_enhanced.py --input doc1.json doc2.json doc3.json --output combined.json

# Pretty console output
python run_enhanced.py --input act.json --format pretty

# Multiple output formats simultaneously
python run_enhanced.py --input batch_input.csv --output-json results.json --output-csv report.csv
```

#### Method C: REST API (Production)
```bash
# Start server
uvicorn main_enhanced:app --reload

# Upload and process JSON file
curl -X POST "http://localhost:8000/api/v2/upload/json?output_format=json" \
  -F "file=@act.json"

# Upload and process CSV file
curl -X POST "http://localhost:8000/api/v2/upload/csv?output_format=csv" \
  -F "file=@batch_input.csv"

# Traditional API endpoint
curl -X POST "http://localhost:8000/api/v1/score" \
  -H "Content-Type: application/json" \
  -d @act.json
```

---

## 📋 Input Formats

### JSON Format (Single Document)
```json
{
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
}
```

### JSON Format (Batch Array)
```json
[
  {
    "document_id": "DOC-001",
    "standardized_data": {...},
    ...
  },
  {
    "document_id": "DOC-002",
    "standardized_data": {...},
    ...
  }
]
```

### CSV Format (Batch Processing)
```csv
document_id,type,amount,vendor,date,currency,line_items,is_valid,errors,warnings,field_coverage,classification_confidence
INV-001,invoice,1250.50,Acme Corp,2025-03-15,USD,5,true,,,0.95,0.94
INV-002,invoice,750.25,Tech Inc,2025-03-20,USD,3,true,,,0.98,0.96
```

**CSV Column Details:**
- `errors`: Pipe-separated (e.g., "error1|error2")
- `warnings`: Pipe-separated (e.g., "warning1|warning2")
- `is_valid`: "true" or "false"

---

## 📤 Output Formats

### JSON Output
```json
{
  "document_id": "DOC-001",
  "summary": "Invoice DOC-001 processed successfully...",
  "risk_score": 0.1234,
  "overall_confidence": 0.95,
  "recommendation": "approve",
  "risk_breakdown": {
    "validation_risk": 0.0,
    "confidence_risk": 0.018,
    "data_completeness_risk": 0.05,
    "anomaly_risk": 0.0
  },
  "flags": [],
  "processed_at": "2025-04-02T12:00:00Z"
}
```

### CSV Output
```csv
document_id,recommendation,risk_score,overall_confidence,validation_risk,confidence_risk,data_completeness_risk,anomaly_risk,summary
DOC-001,approve,0.1234,0.95,0.0,0.018,0.05,0.0,"Invoice processed successfully..."
```

### Pretty Console Output
```
╔══════════════════════════════════════════════════════════════════╗
║                   DOCUMENT ANALYSIS REPORT                       ║
╠══════════════════════════════════════════════════════════════════╣
  Document ID:      DOC-001
  Recommendation:   [APPROVE]
  Risk Score:       0.1234 / 1.00
  Confidence:       95.00%
  Processed At:     2025-04-02T12:00:00Z
----------------------------------------------------------------------
  RISK BREAKDOWN:
    • Validation:     0.0000
    • Confidence:     0.0180
    • Completeness:   0.0500
    • Anomalies:      0.0000
----------------------------------------------------------------------
  SUMMARY:
    Invoice DOC-001 processed successfully. From Acme Corp for 
    USD 1,250.50 dated 2025-03-15. No significant issues detected.
╚══════════════════════════════════════════════════════════════════╝
```

---

## 🎯 Usage Examples

### Example 1: Process Single Document
```bash
python run_enhanced.py --input act.json --output results.json
```

### Example 2: Batch Processing from CSV
```bash
python run_enhanced.py --input batch_input.csv --output report.csv --format csv --verbose
```

### Example 3: Multiple Input Files
```bash
python run_enhanced.py \
  --input invoice1.json invoice2.json invoice3.json \
  --output batch_results.json
```

### Example 4: Pretty Console Output
```bash
python run_enhanced.py --input act.json --format pretty
```

### Example 5: Multiple Output Formats
```bash
python run_enhanced.py \
  --input batch_input.csv \
  --output-json results.json \
  --output-csv report.csv \
  --verbose
```

### Example 6: Programmatic Usage
```python
from run_enhanced import DocumentProcessor
import asyncio

async def main():
    processor = DocumentProcessor()
    
    # Process single file
    results = await processor.process_from_file(
        "act.json",
        output_path="results.json",
        verbose=True
    )
    
    # Process batch
    results = await processor.process_from_file(
        "batch_input.csv",
        input_format=InputFormat.CSV,
        output_path="batch_results.csv",
        output_format=OutputFormat.CSV,
        verbose=True
    )

asyncio.run(main())
```

---

## 🔧 API Endpoints (Enhanced)

### Core Endpoints (v1)
- `POST /api/v1/score` - Score single document
- `POST /api/v1/score/batch` - Score multiple documents
- `GET /api/v1/thresholds` - Get configuration
- `GET /health` - Health check

### New File Upload Endpoints (v2)
- `POST /api/v2/upload/json` - Upload JSON file
- `POST /api/v2/upload/csv` - Upload CSV batch file
- `GET /api/v2/export/template/csv` - Download CSV template
- `GET /api/v2/stats` - Processing statistics

### File Upload Example
```bash
# Upload JSON file and get CSV output
curl -X POST "http://localhost:8000/api/v2/upload/json?output_format=csv" \
  -F "file=@documents.json" \
  -o results.csv

# Upload CSV batch
curl -X POST "http://localhost:8000/api/v2/upload/csv?output_format=json" \
  -F "file=@batch.csv" \
  -o results.json
```

---

## 📊 Batch Processing Performance

The system can efficiently process:
- ✅ Up to **50 documents** per API call (configurable)
- ✅ **Async/parallel** processing for speed
- ✅ **Memory-efficient** streaming for large batches
- ✅ **Progress tracking** in verbose mode

### Batch Summary Output
```json
{
  "results": [...],
  "batch_summary": {
    "total": 100,
    "approved": 75,
    "review": 20,
    "rejected": 5,
    "avg_risk_score": 0.2150,
    "avg_confidence": 0.8923
  }
}
```

---

## 🏗️ Architecture

```
Enhanced Input/Output Flow:
┌─────────────────────────────────────────────────────────────┐
│                     INPUT SOURCES                            │
│  • JSON files (single/batch)                                 │
│  • CSV batch files                                           │
│  • API uploads                                               │
│  • Manual CLI entry                                          │
│  • Programmatic (Python dict)                                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                   IOProcessor                                │
│  ┌──────────────────┐        ┌──────────────────┐          │
│  │  InputHandler    │        │  OutputHandler   │          │
│  │  - from_json     │        │  - to_json       │          │
│  │  - from_csv      │        │  - to_csv        │          │
│  │  - from_dict     │        │  - to_pretty     │          │
│  └──────────────────┘        └──────────────────┘          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  ScoringService                              │
│  (Unchanged - same scoring logic)                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    OUTPUT FORMATS                            │
│  • JSON files                                                │
│  • CSV reports                                               │
│  • Pretty console                                            │
│  • API responses                                             │
│  • Excel (planned)                                           │
│  • PDF (planned)                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 File Structure

```
enhanced-scoring-api/
├── io_handler.py           ⭐ NEW - Input/Output processing
├── run_enhanced.py         ⭐ NEW - Enhanced CLI runner
├── interactive_cli.py      ⭐ NEW - Interactive menu interface
├── main_enhanced.py        ⭐ NEW - Extended FastAPI app
├── batch_input.csv         ⭐ NEW - Sample CSV batch file
│
├── scoring_service.py      (Original - unchanged)
├── risk_scorers.py         (Original - unchanged)
├── summarizer.py           (Original - unchanged)
├── schemas.py              (Original - unchanged)
├── logger.py               (Original - unchanged)
│
├── main.py                 (Original API)
├── run.json                (Original runner)
├── test_scoring.py         (Tests)
├── requirements.txt
└── README_ENHANCED.md      ⭐ This file
```

---

## 🧪 Testing

```bash
# Run all tests
pytest test_scoring.py -v

# Test specific features
pytest test_scoring.py::TestValidationRiskScorer -v
pytest test_scoring.py::TestAPIEndpoints -v

# Test with coverage
pytest --cov=. --cov-report=html
```

---

## 🎓 Command-line Reference

### run_enhanced.py Options

```
Required:
  --input, -i FILE [FILE ...]    Input file(s) to process

Optional:
  --input-format {json,csv}      Input format (default: json)
  --output, -o FILE              Output file path
  --format, -f {json,csv,pretty} Output format (default: json)
  --output-json FILE             Save as JSON
  --output-csv FILE              Save as CSV
  --verbose, -v                  Verbose output
  --quiet, -q                    Suppress output
  --help                         Show help message
```

### Examples:
```bash
# Simplest usage
python run_enhanced.py --input act.json

# Full options
python run_enhanced.py \
  --input batch.csv \
  --input-format csv \
  --output results.json \
  --output-csv report.csv \
  --verbose
```

---

## 🔐 Environment Variables

```bash
# Optional: Enable LLM summaries
export ANTHROPIC_API_KEY=sk-ant-...

# Optional: Database connection
export DATABASE_URL=postgresql://user:pass@localhost/scoring

# Optional: S3 for file storage
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export S3_BUCKET=document-scoring
```

---

## 🚦 Getting Started Checklist

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Try interactive CLI: `python interactive_cli.py`
- [ ] Process sample JSON: `python run_enhanced.py --input act.json`
- [ ] Process sample CSV: `python run_enhanced.py --input batch_input.csv --format csv`
- [ ] Start API server: `uvicorn main_enhanced:app --reload`
- [ ] Upload file via API: Use `/api/v2/upload/json` endpoint
- [ ] Run tests: `pytest test_scoring.py -v`
- [ ] Explore API docs: Visit `http://localhost:8000/docs`

---

## 📚 Additional Resources

- **Original README**: See `README.md` for scoring logic details
- **API Documentation**: http://localhost:8000/docs (when server running)
- **Sample Files**: 
  - `act.json` - Single document example
  - `batch_input.csv` - Batch processing example
  - Download CSV template: `GET /api/v2/export/template/csv`

---

## 🤝 Contributing

To add new input/output formats:

1. Add handler method to `InputHandler` or `OutputHandler` in `io_handler.py`
2. Add enum value to `InputFormat` or `OutputFormat`
3. Update `IOProcessor.load_input()` or `IOProcessor.save_output()`
4. Add tests
5. Update documentation

---

## 📝 License

Same as original project.

---

## 🎉 Summary

**Version 2.0 transforms the scoring system into a versatile tool with:**
- Multiple ways to input data (JSON, CSV, API, manual)
- Multiple output formats (JSON, CSV, console, planned: Excel, PDF)
- Three interfaces (CLI, Interactive, API)
- Batch processing capabilities
- File upload endpoints
- Production-ready architecture

**Choose your workflow:**
- 👨‍💻 Developer? Use `run_enhanced.py` CLI
- 🔰 Beginner? Use `interactive_cli.py` 
- 🏢 Production? Use `main_enhanced.py` API
- 📊 Data Analyst? Use CSV batch processing

All powered by the same robust scoring engine! 🚀

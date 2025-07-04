# Vendor Portal - Packing List Automation System

A comprehensive web-based platform that enables vendors to upload packing lists and invoices for automated processing, price validation, and data extraction. The system supports both Excel (.xlsx/.xls) and PDF file formats with intelligent parsing capabilities.

## Table of Contents

- [Features](#features)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
- [API Documentation](#api-documentation)
- [File Format Support](#file-format-support)
- [Project Structure](#project-structure)
- [Testing](#testing)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

### Core Functionality
- **Multi-format Support**: Process both Excel (.xlsx, .xls) and PDF files
- **Intelligent Parsing**: Advanced text extraction and data recognition
- **Price Validation**: Automatic comparison against backend price database
- **User Authentication**: Secure vendor login system with session management
- **Real-time Processing**: Instant file upload and processing feedback
- **Data Export**: Structured JSON output for integration with other systems

### Advanced Capabilities
- **Multi-sheet Excel Support**: Automatically detects packing list and invoice sheets
- **PDF Text Extraction**: OCR-like capabilities for PDF document processing
- **Price Mismatch Detection**: Identifies discrepancies between packing list and system prices
- **Error Handling**: Comprehensive validation with detailed error reporting
- **File Security**: Secure file upload with automatic cleanup

## Technology Stack

### Backend Framework
- **Flask 3.1.1**: Lightweight web framework for Python
- **Flask-Login 0.6.3**: User session management and authentication
- **Werkzeug 3.1.3**: WSGI web application library

### Data Processing
- **Pandas 2.3.0**: Data manipulation and analysis
- **NumPy 2.3.1**: Numerical computing library
- **OpenPyXL 3.1.5**: Excel file reading and writing

### PDF Processing
- **pdfplumber 0.11.7**: PDF text extraction and table parsing
- **pdfminer.six 20250506**: PDF document analysis
- **pypdfium2 4.30.1**: PDF rendering and manipulation

### Frontend
- **Bootstrap 5**: Responsive CSS framework
- **Jinja2 3.1.6**: Template engine for dynamic HTML generation

### Testing & Development
- **pytest 8.4.1**: Testing framework
- **Cryptography 45.0.5**: Security and encryption utilities

## Prerequisites

Before installing the Vendor Portal, ensure you have the following:

- **Python 3.8 or higher**
- **pip** (Python package installer)
- **virtualenv** (recommended for environment isolation)
- **10GB+ free disk space** (for uploads and temporary processing)
- **Windows 10/Linux/macOS** (Windows PowerShell commands shown in examples)

## Installation

### Step 1: Clone the Repository

```bash
git clone [your-repository-url]
cd vendor-portal
```

### Step 2: Create Virtual Environment

For **Windows PowerShell**:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

For **Windows Command Prompt**:
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

For **Linux/macOS**:
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Create Required Directories

```bash
mkdir uploads
mkdir data
```

### Step 5: Setup Price List (Optional)

Place your price list file at `data/price_list.xlsx` with columns:
- `Item Number`: Product SKU/Item code
- `Vendor Purchase Price`: Price in USD

## Quick Start

### 1. Start the Application

```bash
python run.py
```

### 2. Access the Web Interface

Open your browser and navigate to:
- **Local Access**: http://127.0.0.1:8000
- **Network Access**: http://[your-ip]:8000

### 3. Login

Use the default credentials:
- **Username**: `vendor`
- **Password**: `password123`

### 4. Upload Files

1. Click "Choose File" button
2. Select an Excel (.xlsx/.xls) or PDF file
3. Click "Upload and Process"
4. View the processing results

## Usage Guide

### Supported File Formats

#### Excel Files (.xlsx, .xls)
- **Single Sheet**: Must contain columns for Item Number, Description, Quantity, and optionally Unit Price
- **Multi-Sheet**: System automatically detects packing list and invoice sheets
- **Required Columns**: 
  - Item Number/ItemNo/Item Code
  - Description
  - Quantity/Qty
  - Unit Price (optional)

#### PDF Files (.pdf)
- **Structured Documents**: Works best with tabular data
- **Mixed Content**: Handles documents with both packing list and invoice sections
- **Text Recognition**: Extracts item numbers, descriptions, quantities, and prices

### Processing Workflow

1. **File Upload**: Secure upload with validation
2. **Format Detection**: Automatic file type recognition
3. **Data Parsing**: Intelligent extraction based on file format
4. **Price Enrichment**: Lookup against backend price database
5. **Validation**: Compare packing list prices vs system prices
6. **Result Generation**: Structured JSON output with validation results

### Understanding Results

The system provides detailed results including:

- **Item Information**: SKU, description, quantity
- **Price Comparison**: Packing list price vs system price
- **Validation Status**:
  - ✅ **Price Match**: Prices align within tolerance (±$0.01)
  - ❌ **Price Mismatch**: Significant price difference detected
  - ⚠️ **No Price**: Packing list doesn't contain price information
  - ⚠️ **System Price Not Found**: Item not in backend price database

## API Documentation

### Authentication

All API endpoints require authentication. Login via the web interface or programmatically:

```bash
POST /login
Content-Type: application/x-www-form-urlencoded

username=vendor&password=password123
```

### File Upload and Processing

#### Upload Packing List

**Endpoint**: `POST /`

**Content-Type**: `multipart/form-data`

**Parameters**:
- `file` (required): Excel or PDF file

**Response**: HTML page with processing results and JSON data

**Example JSON Response**:
```json
{
  "status": "success",
  "data": {
    "rows": [
      {
        "sku": "FB50F77B",
        "description": "HYBRID SI 3-IN-1 COMBINATION BOOSTER CAR SEAT",
        "quantity": 640,
        "system_unit_price": 58.05,
        "packing_list_unit_price": 58.05,
        "price_match": true,
        "note": "✅ Price Match",
        "PriceComparisonStatus": "match"
      }
    ],
    "total": 1
  },
  "validation": {
    "price_mismatches": []
  }
}
```

#### Error Responses

**File Format Error**:
```json
{
  "error": "Unsupported file format",
  "supported_formats": ["xlsx", "xls", "pdf"]
}
```

**Processing Error**:
```json
{
  "error": "File processing failed",
  "details": "No valid items found in the file"
}
```

### Session Management

#### Logout

**Endpoint**: `GET /logout`

**Response**: Redirect to login page

## File Format Support

### Excel Requirements

#### Column Mapping
The system recognizes these column names (case-insensitive):
- **Item Number**: `ItemNo`, `Item Number`, `Item Code`, `SKU`, `Product Code`
- **Description**: `Description`, `Product Description`, `Item Description`
- **Quantity**: `Qty`, `Quantity`, `Pieces`, `Units`
- **Unit Price**: `UnitPrice`, `Unit Price`, `Price`, `Cost`

#### Example Excel Structure
```
| ItemNo   | Description                    | Qty | UnitPrice |
|----------|--------------------------------|-----|-----------|
| ABC123   | Widget Type A                  | 100 | 10.50     |
| XYZ789   | Component B                    | 50  | 25.75     |
```

### PDF Requirements

#### Structure Recognition
- **Headers**: Looks for "Packing List", "Invoice", "Commercial Invoice"
- **Tables**: Automatically detects tabular data
- **Item Patterns**: Recognizes patterns like `#ABC123` or `Item: ABC123`
- **Price Patterns**: Extracts monetary values in various formats

#### Best Practices for PDF Processing
1. Use clear, structured layouts
2. Maintain consistent spacing in tables
3. Include clear section headers
4. Avoid heavily stylized fonts
5. Ensure good scan quality for scanned documents

## Project Structure

```
vendor-portal/
├── app/                          # Main application package
│   ├── __init__.py              # Flask app factory
│   ├── auth.py                  # Authentication routes
│   ├── config.py                # Application configuration
│   ├── models.py                # Data models and classes
│   ├── parsing.py               # File parsing logic
│   ├── price_validation.py     # Price validation and enrichment
│   ├── upload.py                # File upload routes
│   ├── static/                  # Static assets
│   │   └── style.css           # Custom styles
│   └── templates/               # HTML templates
│       ├── base.html           # Base template
│       ├── login.html          # Login page
│       ├── result.html         # Results display
│       └── upload.html         # Upload interface
├── data/                        # Data files
│   └── price_list.xlsx         # Backend price database
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── test_integration.py     # Integration tests
│   ├── test_parsing.py         # Parser tests
│   ├── test_price_validation.py # Validation tests
│   └── uploads/                # Test files
├── uploads/                     # Temporary file storage
├── venv/                        # Virtual environment
├── design.md                    # Technical design documentation
├── README.md                    # This file
├── requirements.txt             # Python dependencies
└── run.py                       # Application entry point
```

## Testing

### Running Tests

Execute the complete test suite:
```bash
pytest
```

Run specific test categories:
```bash
# Integration tests
pytest tests/test_integration.py

# Parser tests
pytest tests/test_parsing.py

# Price validation tests
pytest tests/test_price_validation.py
```

Run with verbose output:
```bash
pytest -v
```

### Test Coverage

The test suite covers:
- **Authentication Flow**: Login/logout functionality
- **File Upload**: Valid and invalid file handling
- **Excel Parsing**: Single and multi-sheet files
- **PDF Parsing**: Text extraction and data recognition
- **Price Validation**: System vs packing list price comparison
- **Error Handling**: Various failure scenarios
- **End-to-End Workflows**: Complete user journeys

### Adding Test Files

Place test files in `tests/uploads/`:
- `Packing List_mismatch.xlsx` - Multi-sheet Excel example
- `Packing List_mismatch.pdf` - PDF example with price mismatches

## Configuration

### Environment Variables

Configure the application using environment variables:

```bash
# Security
export SECRET_KEY="your-secret-key-here"
export WTF_CSRF_SECRET_KEY="your-csrf-key-here"

# File Upload
export MAX_CONTENT_LENGTH=10485760  # 10MB in bytes
export UPLOAD_FOLDER="/path/to/uploads"

# Session Management
export PERMANENT_SESSION_LIFETIME=3600  # 1 hour
```

### Application Settings

Key configuration options in `app/config.py`:

- **MAX_CONTENT_LENGTH**: Maximum file upload size (default: 10MB)
- **ALLOWED_EXTENSIONS**: Supported file formats
- **PERMANENT_SESSION_LIFETIME**: User session duration
- **LOG_LEVEL**: Logging verbosity (DEBUG, INFO, WARNING, ERROR)

### Production Deployment

For production deployment:

1. **Change Security Keys**:
   ```bash
   export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex())')"
   export WTF_CSRF_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex())')"
   ```

2. **Use Production WSGI Server**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
   ```

3. **Enable HTTPS**: Configure reverse proxy with SSL/TLS

## Troubleshooting

### Common Issues

#### PowerShell Execution Policy Error
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### PDF Processing Fails
Ensure pdfplumber is properly installed:
```bash
pip install pdfplumber --force-reinstall
```

#### File Upload Size Limit
Increase MAX_CONTENT_LENGTH in config.py or environment variables.

#### Permission Errors on Windows
Run with Administrator privileges or adjust file permissions.

### Debug Mode

Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
python run.py
```

### Log Files

Check application logs for detailed error information:
- Look for "Processing failed" messages
- Check file parsing debug output
- Monitor price validation warnings

## Contributing

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pytest-cov black flake8
   ```
4. Run tests before committing:
   ```bash
   pytest --cov=app
   ```

### Code Style

- Follow PEP 8 guidelines
- Use type hints where possible
- Add docstrings to functions and classes
- Maintain test coverage above 80%

### Submitting Changes

1. Ensure all tests pass
2. Update documentation as needed
3. Submit pull request with clear description

## License

MIT License - see LICENSE file for details.

---

## Support

For technical support or questions:
- Check the [Design Documentation](design.md) for technical details
- Review test files for usage examples
- Open an issue for bug reports or feature requests

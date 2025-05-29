# PDF Web Scraper

A Python script that crawls a given website and downloads all PDF files found on the pages. The scraper is configurable, respects rate limits, and includes proper error handling.

## Features
- Extracts PDF links from web pages
- Downloads PDFs to a specified directory
- Shows progress bar for downloads
- Handles relative and absolute URLs
- Avoids duplicate downloads
- Configurable crawling depth
- Rate limiting to be respectful to servers
- Comprehensive logging
- Unit tests included

## Requirements
- Python 3.7+
- Required packages listed in `requirements.txt`

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/pdf-web-scraper.git
cd pdf-web-scraper
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage
Run the script by providing a URL:
```bash
python pdf_scraper.py --url https://example.com
```

### Advanced Options
```bash
python pdf_scraper.py --url https://example.com \
                     --output-dir custom_downloads \
                     --max-depth 3 \
                     --timeout 45
```

Optional arguments:
- `--output-dir`: Specify the output directory for downloaded PDFs (default: ./downloads)
- `--max-depth`: Maximum depth for crawling (default: 2)
- `--timeout`: Request timeout in seconds (default: 30)

## Configuration

You can modify the default settings in `config.py`:
- Rate limiting
- User agent
- Maximum file size
- Logging settings
- And more

## Testing

Run the unit tests:
```bash
python -m unittest test_pdf_scraper.py
```

## Logging

The scraper logs all activities to both console and file (`pdf_scraper.log`). Log levels can be configured in `config.py`.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

Please ensure you have permission to scrape websites and respect robots.txt files. Some websites may prohibit automated downloading of their content. 
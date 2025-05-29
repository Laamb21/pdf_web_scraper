# Default configuration settings for the PDF scraper

# Scraping settings
DEFAULT_MAX_DEPTH = 2
DEFAULT_TIMEOUT = 30
DEFAULT_OUTPUT_DIR = "downloads"

# Request settings
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# File settings
ALLOWED_EXTENSIONS = ['.pdf']
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB in bytes

# Logging settings
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'
LOG_FILE = 'pdf_scraper.log'

# Rate limiting
REQUESTS_PER_SECOND = 2
DELAY_BETWEEN_REQUESTS = 1 / REQUESTS_PER_SECOND  # in seconds 
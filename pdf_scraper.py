#!/usr/bin/env python3

# Import required libraries
import os  # For file and directory operations
import argparse  # For parsing command line arguments
import requests  # For making HTTP requests
from bs4 import BeautifulSoup  # For parsing HTML content
from urllib.parse import urljoin, urlparse  # For URL manipulation and parsing
from tqdm import tqdm  # For progress bar visualization
import logging  # For logging operations and errors
from pdf_accessibility import PDFAccessibilityChecker, generate_report
from urllib.robotparser import RobotFileParser
import time
from typing import Optional

class PDFScraper:
    """
    A class to scrape PDFs from websites.
    This scraper crawls through web pages up to a specified depth and downloads any PDF files it finds.
    """
    def __init__(self, base_url, output_dir="downloads", timeout=30):
        """
        Initialize the PDF scraper with the given parameters.
        
        Args:
            base_url (str): The starting URL to begin scraping from
            output_dir (str): Directory where PDFs will be saved (default: 'downloads')
            timeout (int): Request timeout in seconds (default: 30)
        """
        self.base_url = base_url
        self.output_dir = output_dir
        self.timeout = timeout
        self.downloaded_pdfs = set()  # Keep track of PDFs we've already downloaded
        self.pdf_sources = {}  # Track the source URL of each downloaded PDF
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Set up logging configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        # Set up robots.txt parser
        self.rp = RobotFileParser()
        self.setup_robots_parser()

    def setup_robots_parser(self):
        """Initialize and fetch robots.txt rules."""
        try:
            # Get the base URL's robots.txt
            parsed_url = urlparse(self.base_url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            self.rp.set_url(robots_url)
            self.rp.read()
            self.logger.info(f"Successfully read robots.txt from {robots_url}")
        except Exception as e:
            self.logger.warning(f"Could not fetch robots.txt: {str(e)}")
            # If we can't fetch robots.txt, we'll assume conservative crawling rules
            self.rp = None

    def can_fetch(self, url):
        """Check if we're allowed to fetch a URL according to robots.txt."""
        try:
            if self.rp is None:
                # If we couldn't fetch robots.txt, use conservative delay
                time.sleep(1)  # Conservative 1 second delay
                return True
            
            # Use 'Python-PDFScraper' as the user agent
            can_fetch = self.rp.can_fetch("Python-PDFScraper", url)
            
            # Respect crawl delay if specified
            crawl_delay = self.rp.crawl_delay("Python-PDFScraper")
            if crawl_delay is not None:
                time.sleep(crawl_delay)
            else:
                # Use conservative delay if none specified
                time.sleep(1)
            
            if not can_fetch:
                self.logger.warning(f"robots.txt disallows accessing: {url}")
            
            return can_fetch
        except Exception as e:
            self.logger.error(f"Error checking robots.txt for {url}: {str(e)}")
            time.sleep(1)  # Conservative delay on error
            return True

    def is_valid_url(self, url):
        """
        Check if a URL belongs to the same domain as the base URL.
        This prevents the scraper from crawling external websites.
        
        Args:
            url (str): The URL to check
            
        Returns:
            bool: True if the URL is valid (same domain or relative), False otherwise
        """
        base_domain = urlparse(self.base_url).netloc
        url_domain = urlparse(url).netloc
        return base_domain in url_domain or not url_domain

    def download_pdf(self, pdf_url: str) -> Optional[str]:
        """Download a PDF file and save it locally."""
        try:
            # Check robots.txt before downloading
            if not self.can_fetch(pdf_url):
                self.logger.warning(f"Skipping {pdf_url} as per robots.txt rules")
                return None

            # Extract the filename from the URL path
            pdf_name = os.path.basename(urlparse(pdf_url).path)
            if not pdf_name.endswith('.pdf'):
                pdf_name += '.pdf'
            
            # Create the full path where the PDF will be saved
            pdf_path = os.path.join(self.output_dir, pdf_name)
            
            # Skip if we've already downloaded this PDF
            if pdf_url in self.downloaded_pdfs:
                self.logger.info(f"Skipping already downloaded PDF: {pdf_name}")
                return pdf_path
            
            # Start the download with streaming enabled for large files
            self.logger.info(f"Downloading: {pdf_name}")
            response = requests.get(pdf_url, stream=True, timeout=self.timeout)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            # Get the file size for the progress bar
            total_size = int(response.headers.get('content-length', 0))
            
            # Download the file with progress tracking
            with open(pdf_path, 'wb') as pdf_file, tqdm(
                desc=pdf_name,
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for data in response.iter_content(chunk_size=1024):
                    size = pdf_file.write(data)
                    pbar.update(size)
              # Mark as downloaded and log success
            self.downloaded_pdfs.add(pdf_url)
            self.logger.info(f"Successfully downloaded: {pdf_name}")
            
            # Save the source URL of the downloaded PDF
            self.pdf_sources[pdf_name] = pdf_url
            
            return pdf_path
        except Exception as e:
            self.logger.error(f"Error downloading PDF from {pdf_url}: {str(e)}")
            return None    
    def scrape_page(self, url):
        """
        Scrape a webpage for PDF links.
        
        Args:
            url (str): The URL of the page to scrape
        """
        # Check robots.txt before scraping
        if not self.can_fetch(url):
            self.logger.warning(f"Skipping {url} as per robots.txt rules")
            return
        
        try:
            # Get and parse the page content
            self.logger.info(f"Scraping page: {url}")
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find and process all PDF links on the page
            for link in soup.find_all('a'):
                href = link.get('href')
                if href and href.lower().endswith('.pdf'):
                    full_url = urljoin(url, href)
                    self.download_pdf(full_url)
                    
        except Exception as e:
            self.logger.error(f"Error scraping {url}: {str(e)}")

def main():
    """
    Main entry point of the script.
    Sets up argument parsing and initiates the scraping process.
    """
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Simple PDF scraper with legal compliance')
    parser.add_argument('--url', required=True, help='Website URL to scrape PDFs from')
    parser.add_argument('--output-dir', default='downloads', help='Directory to save PDFs')
    parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds')
    
    args = parser.parse_args()
      # Create and configure the scraper
    scraper = PDFScraper(
        args.url,
        output_dir=args.output_dir,
        timeout=args.timeout
    )
    
    # Start the scraping process
    print(f"Starting to scrape PDFs from {args.url}")
    scraper.scrape_page(args.url)
    print(f"\nScraping completed! PDFs have been saved to: {args.output_dir}")

if __name__ == "__main__":
    main()
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

class PDFScraper:
    """
    A class to scrape PDFs from websites.
    This scraper crawls through web pages up to a specified depth and downloads any PDF files it finds.
    """
    
    def __init__(self, base_url, output_dir="downloads", max_depth=2, timeout=30):
        """
        Initialize the PDF scraper with the given parameters.
        
        Args:
            base_url (str): The starting URL to begin scraping from
            output_dir (str): Directory where PDFs will be saved (default: 'downloads')
            max_depth (int): Maximum depth of pages to crawl (default: 2)
            timeout (int): Request timeout in seconds (default: 30)
        """
        self.base_url = base_url
        self.output_dir = output_dir
        self.max_depth = max_depth
        self.timeout = timeout
        self.visited_urls = set()  # Keep track of URLs we've already visited
        self.downloaded_pdfs = set()  # Keep track of PDFs we've already downloaded
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Set up logging configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

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

    def download_pdf(self, pdf_url):
        """
        Download a PDF file from the given URL with progress tracking.
        
        Args:
            pdf_url (str): The URL of the PDF to download
            
        The function handles:
        - Extracting filename from URL
        - Skipping already downloaded files
        - Showing download progress
        - Error handling and logging
        """
        try:
            # Extract the filename from the URL path
            pdf_name = os.path.basename(urlparse(pdf_url).path)
            if not pdf_name.endswith('.pdf'):
                pdf_name += '.pdf'
            
            # Create the full path where the PDF will be saved
            pdf_path = os.path.join(self.output_dir, pdf_name)
            
            # Skip if we've already downloaded this PDF
            if pdf_url in self.downloaded_pdfs:
                self.logger.info(f"Skipping already downloaded PDF: {pdf_name}")
                return
            
            # Start the download with streaming enabled for large files
            response = requests.get(pdf_url, stream=True, timeout=self.timeout)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            # Get the file size for the progress bar
            total_size = int(response.headers.get('content-length', 0))
            
            # Download the file with progress tracking
            self.logger.info(f"Downloading: {pdf_name}")
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
            
            # Check accessibility after download
            if hasattr(self, 'check_accessibility') and self.check_accessibility:
                checker = PDFAccessibilityChecker(self.output_dir)
                result = checker.check_single_pdf(pdf_path)
                if not result['is_compliant']:
                    self.logger.warning(f"{pdf_name} is not 508 compliant")
                    for issue in result.get('issues', []):
                        self.logger.warning(f"- {issue['rule']}: {issue['description']}")
            
        except Exception as e:
            self.logger.error(f"Error downloading PDF from {pdf_url}: {str(e)}")

    def scrape_page(self, url, depth=0):
        """
        Recursively scrape a webpage for PDF links and other pages to crawl.
        
        Args:
            url (str): The URL of the page to scrape
            depth (int): Current depth in the crawling hierarchy
            
        The function:
        - Checks depth limits and already visited pages
        - Parses HTML content for links
        - Downloads PDFs when found
        - Recursively crawls valid pages
        """
        # Stop if we've reached max depth or already visited this URL
        if depth > self.max_depth or url in self.visited_urls:
            return
        
        self.visited_urls.add(url)
        
        try:
            # Get and parse the page content
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find and process all links on the page
            for link in soup.find_all('a'):
                href = link.get('href')
                if not href:
                    continue
                
                # Convert relative URLs to absolute URLs
                full_url = urljoin(url, href)
                
                # Handle PDFs and valid pages differently
                if full_url.lower().endswith('.pdf'):
                    self.download_pdf(full_url)
                elif self.is_valid_url(full_url):
                    self.scrape_page(full_url, depth + 1)
                    
        except Exception as e:
            self.logger.error(f"Error scraping {url}: {str(e)}")

def main():
    """
    Main entry point of the script.
    Sets up argument parsing and initiates the scraping process.
    """
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Web scraper for downloading PDFs from a website')
    parser.add_argument('--url', required=True, help='The website URL to scrape')
    parser.add_argument('--output-dir', default='downloads', help='Directory to save PDFs')
    parser.add_argument('--max-depth', type=int, default=2, help='Maximum crawling depth')
    parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds')
    parser.add_argument('--check-508', action='store_true', help='Check PDFs for 508 compliance')
    parser.add_argument('--accessibility-report', default='accessibility_report.txt',
                      help='Output file for accessibility report')
    
    args = parser.parse_args()
    
    # Create and configure the scraper
    scraper = PDFScraper(
        args.url,
        output_dir=args.output_dir,
        max_depth=args.max_depth,
        timeout=args.timeout
    )
    
    # Add accessibility checking flag
    scraper.check_accessibility = args.check_508
    
    # Start the scraping process
    print(f"Starting to scrape PDFs from {args.url}")
    scraper.scrape_page(args.url)
    print(f"\nScraping completed! PDFs have been saved to: {args.output_dir}")
    
    # Generate accessibility report if requested
    if args.check_508:
        print("\nChecking downloaded PDFs for 508 compliance...")
        checker = PDFAccessibilityChecker(args.output_dir)
        results = checker.check_directory()
        generate_report(results, args.accessibility_report)
        print(f"Accessibility report generated: {args.accessibility_report}")

if __name__ == "__main__":
    main() 
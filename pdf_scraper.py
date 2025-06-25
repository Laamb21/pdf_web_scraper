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
import certifi
from typing import Optional, Set
from collections import deque

class PDFScraper:
    """
    A class to scrape PDFs from websites.
    This scraper crawls through web pages up to a specified depth and downloads any PDF files it finds.
    """
    def __init__(self, base_url, output_dir="downloads", timeout=30, verify_ssl=True, max_depth=3):
        """
        Initialize the PDF scraper with the given parameters.
        
        Args:
            base_url (str): The starting URL to begin scraping from
            output_dir (str): Directory where PDFs will be saved (default: 'downloads')
            timeout (int): Request timeout in seconds (default: 30)
            verify_ssl (bool): Whether to verify SSL certificates (default: True)
            max_depth (int): Maximum depth to crawl (default: 3)
        """
        # Set up logging configuration first
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        # Initialize core attributes
        self.base_url = base_url
        self.base_domain = urlparse(base_url).netloc
        self.output_dir = output_dir
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.max_depth = max_depth
        self.session = requests.Session()
        
        # Initialize tracking collections
        self.visited_urls = set()         # URLs that have been crawled
        self.found_pdfs = set()           # PDF URLs that have been found
        self.downloaded_pdfs = set()      # PDF URLs that have been successfully downloaded
        self.pdf_sources = {}             # Mapping of PDF filenames to their source URLs
        self.failed_downloads = {}        # PDF URLs that failed to download and why
        self.skipped_pdfs = {}           # PDF URLs that were skipped and why
        
        # Configure SSL verification
        if verify_ssl:
            self.session.verify = certifi.where()
        else:
            self.session.verify = False
            # Disable SSL verification warnings if verify_ssl is False
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            self.logger.warning("SSL certificate verification is disabled. This is not recommended for production use.")

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
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
            
    def is_valid_url(self, url: str) -> bool:
        """
        Check if a URL is valid for crawling.
        
        Args:
            url (str): The URL to validate
            
        Returns:
            bool: True if the URL is valid (same domain, not mailto, etc.), False otherwise
        """
        # Skip mailto: links and other email-related URLs
        if url.startswith(('mailto:', 'tel:', 'sms:', 'fax:')):
            return False
            
        # Parse the URL
        try:
            parsed = urlparse(url)
        except Exception:
            return False
            
        # Skip if no domain (might be a javascript: link or other invalid URL)
        if not parsed.netloc and not parsed.path:
            return False
            
        # Skip email addresses in any form
        if '@' in url:
            return False
            
        # Check domain
        base_domain = urlparse(self.base_url).netloc
        url_domain = parsed.netloc
        
        # Either should be same domain or a relative URL
        return base_domain in url_domain or not url_domain

    def download_pdf(self, pdf_url: str) -> Optional[str]:
        """Download a PDF file and save it locally."""
        try:
            # Check robots.txt before downloading
            if not self.can_fetch(pdf_url):
                self.skipped_pdfs[pdf_url] = "Blocked by robots.txt"
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
                self.skipped_pdfs[pdf_url] = "Already downloaded"
                self.logger.info(f"Skipping already downloaded PDF: {pdf_name}")
                return pdf_path
            
            # Start the download with streaming enabled for large files
            self.logger.info(f"Downloading: {pdf_name}")
            try:
                response = self.session.get(pdf_url, stream=True, timeout=self.timeout)
                response.raise_for_status()  # Raise an exception for bad status codes
                
                # Verify content type is PDF
                content_type = response.headers.get('content-type', '').lower()
                if 'pdf' not in content_type and 'application/octet-stream' not in content_type:
                    self.failed_downloads[pdf_url] = f"Invalid content type: {content_type}"
                    self.logger.warning(f"Skipping non-PDF content type: {content_type} for {pdf_name}")
                    return None

            except requests.exceptions.SSLError as ssl_err:
                self.failed_downloads[pdf_url] = f"SSL Error: {str(ssl_err)}"
                self.logger.error(f"SSL Error when downloading {pdf_url}: {str(ssl_err)}")
                if self.verify_ssl:
                    self.logger.warning("Consider using --no-verify-ssl if the site has a valid but unverifiable certificate")
                return None
            except requests.exceptions.RequestException as req_err:
                self.failed_downloads[pdf_url] = f"Request Error: {str(req_err)}"
                self.logger.error(f"Request error when downloading {pdf_url}: {str(req_err)}")
                return None
            
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
            
            # Verify the downloaded file is actually a PDF
            try:
                with open(pdf_path, 'rb') as f:
                    if not f.read(4).startswith(b'%PDF'):
                        os.remove(pdf_path)
                        self.failed_downloads[pdf_url] = "Not a valid PDF file"
                        self.logger.warning(f"Removed invalid PDF file: {pdf_name}")
                        return None
            except Exception as e:
                os.remove(pdf_path)
                self.failed_downloads[pdf_url] = f"PDF verification failed: {str(e)}"
                return None

            # Mark as downloaded and log success
            self.downloaded_pdfs.add(pdf_url)
            self.logger.info(f"Successfully downloaded: {pdf_name}")
            
            # Save the source URL of the downloaded PDF
            self.pdf_sources[pdf_name] = pdf_url
            
            return pdf_path
        except Exception as e:
            self.failed_downloads[pdf_url] = f"Unexpected error: {str(e)}"
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

    def normalize_url(self, url: str) -> str:
        """Normalize URL to avoid duplicates with different representations."""
        parsed = urlparse(url)
        # Remove fragments and normalize path
        normalized = parsed._replace(fragment='').geturl()
        return normalized.rstrip('/')

    def extract_links(self, soup: BeautifulSoup, current_url: str) -> set:
        """Extract all valid links from a BeautifulSoup object."""
        links = set()
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            if not href:
                continue
                
            # Skip email addresses and invalid URLs
            if href.startswith('#') or href.startswith('javascript:'):
                continue
                
            # Convert relative URLs to absolute
            absolute_url = urljoin(current_url, href)
            normalized_url = self.normalize_url(absolute_url)
            
            # Check if URL belongs to the same domain and hasn't been visited
            if self.is_valid_url(normalized_url) and normalized_url not in self.visited_urls:
                links.add(normalized_url)
                
        return links

    def crawl(self):
        """Crawl the website starting from base_url up to max_depth."""
        # Queue of (url, depth) pairs to process
        queue = deque([(self.base_url, 0)])
        self.visited_urls.clear()
        self.found_pdfs.clear()
        
        with tqdm(desc="Crawling URLs", unit="page") as pbar:
            while queue:
                current_url, depth = queue.popleft()
                
                # Skip if we've reached max depth or already visited
                if depth > self.max_depth or current_url in self.visited_urls:
                    continue
                
                # Mark as visited
                self.visited_urls.add(current_url)
                
                try:
                    # Check robots.txt before accessing
                    if not self.can_fetch(current_url):
                        continue
                        
                    # Fetch and parse the page
                    response = self.session.get(current_url, timeout=self.timeout)
                    response.raise_for_status()
                    
                    # Update progress
                    pbar.update(1)
                    pbar.set_postfix({"depth": depth, "queue": len(queue)})
                    
                    # Parse HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract and process PDF links
                    self.process_pdf_links(soup, current_url)
                    
                    # If we haven't reached max depth, add new links to queue
                    if depth < self.max_depth:
                        new_links = self.extract_links(soup, current_url)
                        for link in new_links:
                            if link not in self.visited_urls:
                                queue.append((link, depth + 1))
                                
                except Exception as e:
                    self.logger.error(f"Error processing {current_url}: {str(e)}")
                    continue
        
        # Print crawling summary
        self.logger.info(f"\nCrawling completed:")
        self.logger.info(f"Total pages visited: {len(self.visited_urls)}")
        self.logger.info(f"Total PDFs found: {len(self.found_pdfs)}")
        self.logger.info(f"Total PDFs downloaded: {len(self.downloaded_pdfs)}")

    def process_pdf_links(self, soup: BeautifulSoup, source_url: str):
        """Extract and process PDF links from a page."""
        for link in soup.find_all('a', href=True):
            href = link['href']
            if not href:
                continue
                
            # Convert relative URLs to absolute
            pdf_url = urljoin(source_url, href)
            
            # Check if it's a PDF link
            if pdf_url.lower().endswith('.pdf') and pdf_url not in self.found_pdfs:
                self.found_pdfs.add(pdf_url)
                self.download_pdf(pdf_url)

    def print_summary(self):
        """Print a detailed summary of the crawling and download results."""
        self.logger.info("\nDetailed Crawling Summary:")
        self.logger.info("-" * 50)
        self.logger.info(f"Total pages visited: {len(self.visited_urls)}")
        self.logger.info(f"Total PDFs found: {len(self.found_pdfs)}")
        self.logger.info(f"Successfully downloaded: {len(self.downloaded_pdfs)}")
        
        if self.skipped_pdfs:
            self.logger.info("\nSkipped PDFs:")
            for url, reason in self.skipped_pdfs.items():
                self.logger.info(f"- {os.path.basename(url)}: {reason}")
        
        if self.failed_downloads:
            self.logger.info("\nFailed Downloads:")
            for url, reason in self.failed_downloads.items():
                self.logger.info(f"- {os.path.basename(url)}: {reason}")

        self.logger.info("-" * 50)

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
    parser.add_argument('--no-verify-ssl', action='store_true', 
                      help='Disable SSL certificate verification (not recommended)')
    parser.add_argument('--max-depth', type=int, default=3,
                      help='Maximum depth to crawl (default: 3)')
    
    args = parser.parse_args()
    
    # Create and configure the scraper
    scraper = PDFScraper(
        args.url,
        output_dir=args.output_dir,
        timeout=args.timeout,
        verify_ssl=not args.no_verify_ssl,
        max_depth=args.max_depth
    )
      # Start the scraping process
    print(f"Starting to crawl from {args.url}")
    print(f"Maximum depth: {args.max_depth}")
    scraper.crawl()
    scraper.print_summary()
    print(f"\nScraping completed! PDFs have been saved to: {args.output_dir}")

if __name__ == "__main__":
    main()
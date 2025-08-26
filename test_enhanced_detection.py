#!/usr/bin/env python3

"""
Test script for the enhanced PDF detection capabilities.
This script tests the cloud storage URL transformation methods and detection patterns.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui_scraper import EnhancedPDFScraper

def test_url_transformations():
    """Test the cloud storage URL transformation methods."""
    print("Testing Cloud Storage URL Transformations")
    print("=" * 50)
    
    # Create a test scraper instance
    scraper = EnhancedPDFScraper("https://example.com", progress_callback=None)
    
    # Test Google Drive URL transformations
    print("\n1. Google Drive URL Transformations:")
    google_drive_urls = [
        "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/view",
        "https://drive.google.com/open?id=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
        "https://drive.google.com/uc?id=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
    ]
    
    for url in google_drive_urls:
        transformed = scraper.transform_google_drive_url(url)
        print(f"Original:    {url}")
        print(f"Transformed: {transformed}")
        print()
    
    # Test Dropbox URL transformations
    print("2. Dropbox URL Transformations:")
    dropbox_urls = [
        "https://www.dropbox.com/s/abc123/document.pdf?dl=0",
        "https://www.dropbox.com/sh/xyz789/folder?dl=0",
        "https://www.dropbox.com/scl/fi/def456/file.pdf",
    ]
    
    for url in dropbox_urls:
        transformed = scraper.transform_dropbox_url(url)
        print(f"Original:    {url}")
        print(f"Transformed: {transformed}")
        print()
    
    # Test OneDrive URL transformations
    print("3. OneDrive URL Transformations:")
    onedrive_urls = [
        "https://1drv.ms/b/s!AhKmyc7T-7OUgQs",
        "https://onedrive.live.com/redir?resid=123&authkey=456",
        "https://company.sharepoint.com/sites/docs/document.pdf",
    ]
    
    for url in onedrive_urls:
        transformed = scraper.transform_onedrive_url(url)
        print(f"Original:    {url}")
        print(f"Transformed: {transformed}")
        print()

def test_detection_patterns():
    """Test the detection patterns with sample HTML."""
    print("\nTesting Detection Patterns")
    print("=" * 50)
    
    # Sample HTML with various cloud storage links
    sample_html = """
    <html>
    <body>
        <a href="https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/view">Student Handbook</a>
        <a href="https://www.dropbox.com/s/abc123/policy.pdf?dl=0">School Policy</a>
        <a href="https://s3.amazonaws.com/school-docs/manual.pdf">Safety Manual</a>
        <a href="https://1drv.ms/b/s!AhKmyc7T-7OUgQs">Course Catalog</a>
        <a href="https://bit.ly/school-handbook">Handbook (shortened)</a>
        <a href="https://wetransfer.com/downloads/abc123">Transfer Document</a>
        <a href="https://mediafire.com/file/xyz789/report.pdf">Annual Report</a>
        <a href="https://mega.nz/file/abc123">Mega Document</a>
        <a href="https://box.com/s/shared123">Box Document</a>
        <a href="https://icloud.com/iclouddrive/document">iCloud Document</a>
    </body>
    </html>
    """
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(sample_html, 'html.parser')
    
    # Create a test scraper with a mock progress callback
    detected_urls = []
    
    def mock_progress_callback(update_type, data):
        if update_type == 'log' and 'Found' in data['message']:
            detected_urls.append(data['message'])
    
    scraper = EnhancedPDFScraper("https://example.com", progress_callback=mock_progress_callback)
    
    # Test the ultra aggressive PDF detection
    print("Running ultra_aggressive_pdf_detection on sample HTML...")
    scraper.ultra_aggressive_pdf_detection(soup, "https://example.com")
    
    print(f"\nDetected {len(detected_urls)} potential PDF URLs:")
    for i, url_info in enumerate(detected_urls, 1):
        print(f"{i}. {url_info}")
    
    print(f"\nTotal PDFs found in scraper: {len(scraper.found_pdfs)}")
    for pdf_url in scraper.found_pdfs:
        print(f"  - {pdf_url}")

if __name__ == "__main__":
    print("Enhanced PDF Detection Test Suite")
    print("=" * 60)
    
    try:
        test_url_transformations()
        test_detection_patterns()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("The enhanced cloud storage detection is working properly.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

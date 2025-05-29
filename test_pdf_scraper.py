import unittest
from unittest.mock import patch, MagicMock
from pdf_scraper import PDFScraper
import os
import tempfile
import shutil

class TestPDFScraper(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        self.test_dir = tempfile.mkdtemp()
        self.scraper = PDFScraper(
            base_url="https://example.com",
            output_dir=self.test_dir
        )

    def tearDown(self):
        """Clean up test environment after each test."""
        shutil.rmtree(self.test_dir)

    def test_is_valid_url(self):
        """Test URL validation logic."""
        # Same domain should be valid
        self.assertTrue(self.scraper.is_valid_url("https://example.com/path"))
        self.assertTrue(self.scraper.is_valid_url("https://sub.example.com/path"))
        
        # Different domains should be invalid
        self.assertFalse(self.scraper.is_valid_url("https://different.com/path"))
        
        # Relative URLs should be valid
        self.assertTrue(self.scraper.is_valid_url("/relative/path"))

    @patch('requests.get')
    def test_download_pdf(self, mock_get):
        """Test PDF download functionality."""
        # Mock successful PDF download
        mock_response = MagicMock()
        mock_response.headers = {'content-length': '100'}
        mock_response.iter_content.return_value = [b'fake pdf content']
        mock_get.return_value = mock_response

        self.scraper.download_pdf("https://example.com/test.pdf")
        
        # Check if file was created
        expected_file = os.path.join(self.test_dir, "test.pdf")
        self.assertTrue(os.path.exists(expected_file))

    @patch('requests.get')
    def test_scrape_page(self, mock_get):
        """Test web page scraping functionality."""
        # Mock HTML content with PDF links
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <a href="/document1.pdf">PDF 1</a>
                <a href="https://example.com/document2.pdf">PDF 2</a>
                <a href="https://example.com/page">Another Page</a>
            </body>
        </html>
        """
        mock_get.return_value = mock_response

        with patch.object(self.scraper, 'download_pdf') as mock_download:
            self.scraper.scrape_page("https://example.com")
            # Should attempt to download 2 PDFs
            self.assertEqual(mock_download.call_count, 2)

    def test_output_directory_creation(self):
        """Test if output directory is created correctly."""
        test_dir = os.path.join(self.test_dir, "nested", "pdf_output")
        scraper = PDFScraper(
            base_url="https://example.com",
            output_dir=test_dir
        )
        self.assertTrue(os.path.exists(test_dir))

if __name__ == '__main__':
    unittest.main() 
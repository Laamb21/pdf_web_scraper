#!/usr/bin/env python3

import os
from typing import Dict, List, Optional
from PyPDF2 import PdfReader
from pdfminer.high_level import extract_text
from pdfminer.layout import LAParams, LTTextBox, LTImage
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
import io
import logging
from datetime import datetime

class PDFAccessibilityChecker:
    """
    A class to check PDF files for Section 508 compliance using PyPDF2 and pdfminer.six.
    """
    
    def __init__(self, pdf_directory: str):
        """
        Initialize the PDF accessibility checker.
        
        Args:
            pdf_directory (str): Directory containing PDF files to check
        """
        self.pdf_directory = pdf_directory
        self.logger = logging.getLogger(__name__)
    
    def check_single_pdf(self, pdf_path: str, source_url: str = None) -> Dict:
        """Check a single PDF file for accessibility compliance."""
        try:
            # Read the PDF using PyPDF2 and get accurate page count
            with open(pdf_path, 'rb') as file:
                try:
                    pdf = PdfReader(file)
                    page_count = len(pdf.pages)
                except Exception as e:
                    self.logger.error(f"Error reading PDF pages: {str(e)}")
                    page_count = 0

                # Initialize results with URL and page count
                results = {
                    'filename': os.path.basename(pdf_path),
                    'is_compliant': True,
                    'issues': [],
                    'metadata': self._check_metadata(pdf),
                    'structure': self._check_structure(pdf),
                    'text': self._check_text_accessibility(pdf_path),
                    'page_count': page_count,  # Make sure page_count is included
                    'source_url': source_url
                }
                
                # Check for common accessibility issues
                self._check_accessibility_issues(pdf, results)
                
                return results
                
        except Exception as e:
            self.logger.error(f"Error checking PDF {pdf_path}: {str(e)}")
            return {
                'filename': os.path.basename(pdf_path),
                'is_compliant': False,
                'error': str(e),
                'page_count': 0,
                'source_url': source_url
            }
    
    def _check_accessibility_issues(self, pdf: PdfReader, results: Dict):
        """Check for various accessibility issues and update results."""
        # Check for basic requirements
        if not results['metadata']['has_title']:
            self._add_issue(results, 'Missing Title', 'Document lacks a title', 'High')
        
        if not results['metadata']['has_language']:
            self._add_issue(results, 'Missing Language', 'Document language not specified', 'High')
        
        if not results['structure']['has_bookmarks'] and results['structure']['total_pages'] > 20:
            self._add_issue(results, 'Missing Bookmarks', 
                          'Large document lacks bookmarks for navigation', 'Medium')
        
        if not results['text']['has_text']:
            self._add_issue(results, 'No Extractable Text', 
                          'Document may be image-only without OCR', 'High')
        
        # Check text quality
        if results['text']['text_quality'] == 'poor':
            self._add_issue(results, 'Poor Text Quality', 
                          'Text content may be difficult to extract or read', 'Medium')
        
        # Check for images without alternative text
        if results['text']['images_without_alt_text'] > 0:
            self._add_issue(results, 'Missing Alt Text',
                          f'Found {results["text"]["images_without_alt_text"]} images without alternative text',
                          'High')
    
    def _add_issue(self, results: Dict, rule: str, description: str, severity: str):
        """Add an issue to the results and mark as non-compliant."""
        results['is_compliant'] = False
        results['issues'].append({
            'rule': rule,
            'description': description,
            'severity': severity
        })
    
    def check_directory(self) -> List[Dict]:
        """
        Check all PDFs in the directory for accessibility compliance.
        
        Returns:
            List[Dict]: Results for all PDFs
        """
        results = []
        
        for filename in os.listdir(self.pdf_directory):
            if filename.lower().endswith('.pdf'):
                pdf_path = os.path.join(self.pdf_directory, filename)
                result = self.check_single_pdf(pdf_path)
                results.append(result)
                
                # Log the results
                if result.get('is_compliant'):
                    self.logger.info(f"{filename} is 508 compliant")
                else:
                    self.logger.warning(f"{filename} is not 508 compliant")
                    for issue in result.get('issues', []):
                        self.logger.warning(f"- {issue['rule']}: {issue['description']}")
        
        return results
    
    def _check_metadata(self, pdf: PdfReader) -> Dict:
        """Check PDF metadata for accessibility requirements."""
        metadata = pdf.metadata if pdf.metadata else {}
        return {
            'has_title': bool(metadata.get('/Title')),
            'has_author': bool(metadata.get('/Author')),
            'has_subject': bool(metadata.get('/Subject')),
            'has_language': bool(metadata.get('/Lang'))
        }
    
    def _check_structure(self, pdf: PdfReader) -> Dict:
        """Check PDF structure for accessibility requirements."""
        return {
            'has_bookmarks': len(pdf.outline) > 0,
            'total_pages': len(pdf.pages),
            'has_tags': '/StructTreeRoot' in pdf.trailer['/Root']
            if '/Root' in pdf.trailer else False
        }
    
    def _check_text_accessibility(self, pdf_path: str) -> Dict:
        """
        Check text accessibility features using pdfminer.six for more detailed analysis.
        """
        results = {
            'has_text': False,
            'has_ocr': False,
            'text_quality': 'unknown',
            'images_without_alt_text': 0,
            'reading_order': 'unknown'
        }
        
        try:
            # Extract text using pdfminer
            text = extract_text(pdf_path)
            results['has_text'] = bool(text.strip())
            
            # Analyze text quality
            if results['has_text']:
                text_length = len(text)
                if text_length > 1000:
                    results['text_quality'] = 'good'
                elif text_length > 100:
                    results['text_quality'] = 'fair'
                else:
                    results['text_quality'] = 'poor'
            
            # Check for images and their properties
            rsrcmgr = PDFResourceManager()
            laparams = LAParams()
            device = PDFPageAggregator(rsrcmgr, laparams=laparams)
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            
            with open(pdf_path, 'rb') as file:
                for page in PDFPage.get_pages(file):
                    interpreter.process_page(page)
                    layout = device.get_result()
                    
                    # Count images without alternative text
                    for element in layout:
                        if isinstance(element, LTImage):
                            # Check if image has associated text nearby
                            has_alt_text = False
                            for text_elem in layout:
                                if isinstance(text_elem, LTTextBox):
                                    if self._is_near_image(element, text_elem):
                                        has_alt_text = True
                                        break
                            
                            if not has_alt_text:
                                results['images_without_alt_text'] += 1
            
            # Detect possible OCR
            if results['has_text'] and results['images_without_alt_text'] > 0:
                results['has_ocr'] = True
            
        except Exception as e:
            self.logger.error(f"Error checking text accessibility: {str(e)}")
        
        return results
    
    def _is_near_image(self, image, text_elem, threshold=50):
        """Check if text element is near an image (potential alt text)."""
        image_bbox = image.bbox
        text_bbox = text_elem.bbox
        
        # Check if text is above, below, or beside the image within threshold
        return (abs(image_bbox[1] - text_bbox[3]) < threshold or  # text above
                abs(image_bbox[3] - text_bbox[1]) < threshold or  # text below
                abs(image_bbox[0] - text_bbox[2]) < threshold or  # text left
                abs(image_bbox[2] - text_bbox[0]) < threshold)    # text right

def generate_report(results: List[Dict], output_file: str = "accessibility_report.txt", source_url: str = None):
    """Generate an accessibility report with summary statistics and compliance details."""
    total_pdfs = len(results)
    compliant_pdfs = sum(1 for result in results if result['is_compliant'])
    non_compliant_pdfs = total_pdfs - compliant_pdfs
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Write timestamp and summary statistics
        f.write("PDF Accessibility Compliance Report\n")
        f.write(f"Generated: {timestamp}\n")
        f.write(f"Website URL: {source_url or 'Not specified'}\n")
        f.write("=====================================\n\n")
        f.write("Summary Statistics\n")
        f.write("-----------------\n")
        f.write(f"Total PDFs Found: {total_pdfs}\n")
        f.write(f"508 Compliant: {compliant_pdfs}\n")
        f.write(f"Non-compliant: {non_compliant_pdfs}\n")
        f.write("\nDetailed Results\n")
        f.write("---------------\n\n")
        
        # Write individual results
        for result in results:
            f.write(f"File: {result['filename']}\n")
            source_url = result.get('source_url', result.get('pdf_url', 'Unknown location'))
            f.write(f"Source URL: {source_url}\n")
            f.write(f"Compliance Status: {'[PASS] Compliant' if result['is_compliant'] else '[FAIL] Non-compliant'}\n")
            f.write(f"Pages: {result.get('page_count', 'Unknown')}\n")
            f.write("\n" + "=" * 50 + "\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Check PDFs for 508 compliance')
    parser.add_argument('--dir', required=True, help='Directory containing PDFs to check')
    parser.add_argument('--report', default='accessibility_report.txt', help='Output report file')
    parser.add_argument('--url', help='Website URL that was scraped')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    checker = PDFAccessibilityChecker(args.dir)
    results = checker.check_directory()
    generate_report(results, args.report, args.url)
    print(f"\nAccessibility report generated: {args.report}")
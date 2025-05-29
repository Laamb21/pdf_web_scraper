#!/usr/bin/env python3

import os
from typing import Dict, List, Optional
from PyPDF2 import PdfReader
from pdf_accessibility_checker.checker import AccessibilityChecker
from pdf_accessibility_checker.rules import Rule
import logging

class PDFAccessibilityChecker:
    """
    A class to check PDF files for Section 508 compliance.
    """
    
    def __init__(self, pdf_directory: str):
        """
        Initialize the PDF accessibility checker.
        
        Args:
            pdf_directory (str): Directory containing PDF files to check
        """
        self.pdf_directory = pdf_directory
        self.logger = logging.getLogger(__name__)
        
    def check_single_pdf(self, pdf_path: str) -> Dict:
        """
        Check a single PDF file for accessibility compliance.
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            Dict: Results of accessibility checks
        """
        try:
            # Initialize the accessibility checker
            checker = AccessibilityChecker()
            
            # Read the PDF
            pdf = PdfReader(pdf_path)
            
            results = {
                'filename': os.path.basename(pdf_path),
                'is_compliant': True,
                'issues': [],
                'metadata': self._check_metadata(pdf),
                'structure': self._check_structure(pdf),
                'text': self._check_text_accessibility(pdf)
            }
            
            # Run the accessibility checker
            checker_results = checker.check(pdf_path)
            
            # Process results
            for rule, rule_result in checker_results.items():
                if not rule_result.passed:
                    results['is_compliant'] = False
                    results['issues'].append({
                        'rule': rule,
                        'description': rule_result.message,
                        'severity': rule_result.severity
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error checking PDF {pdf_path}: {str(e)}")
            return {
                'filename': os.path.basename(pdf_path),
                'is_compliant': False,
                'error': str(e)
            }
    
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
            'has_tags': pdf.is_encrypted
        }
    
    def _check_text_accessibility(self, pdf: PdfReader) -> Dict:
        """Check text accessibility features."""
        results = {
            'has_text': False,
            'has_ocr': False,
            'text_quality': 'unknown'
        }
        
        try:
            # Check first page for text
            page = pdf.pages[0]
            text = page.extract_text()
            results['has_text'] = bool(text.strip())
            
            # Basic OCR detection (presence of text when there's also images)
            if '/XObject' in page and results['has_text']:
                results['has_ocr'] = True
            
            # Rough text quality assessment
            if results['has_text']:
                text_length = len(text)
                if text_length > 100:
                    results['text_quality'] = 'good'
                elif text_length > 20:
                    results['text_quality'] = 'fair'
                else:
                    results['text_quality'] = 'poor'
        
        except Exception as e:
            self.logger.error(f"Error checking text accessibility: {str(e)}")
        
        return results

def generate_report(results: List[Dict], output_file: str = "accessibility_report.txt"):
    """
    Generate a detailed accessibility report.
    
    Args:
        results (List[Dict]): Results from PDF checks
        output_file (str): Path to save the report
    """
    with open(output_file, 'w') as f:
        f.write("PDF Accessibility Compliance Report\n")
        f.write("================================\n\n")
        
        compliant_count = sum(1 for r in results if r.get('is_compliant'))
        total_count = len(results)
        
        f.write(f"Summary:\n")
        f.write(f"- Total PDFs checked: {total_count}\n")
        f.write(f"- Compliant PDFs: {compliant_count}\n")
        f.write(f"- Non-compliant PDFs: {total_count - compliant_count}\n\n")
        
        for result in results:
            f.write(f"\nFile: {result['filename']}\n")
            f.write("-" * (len(result['filename']) + 6) + "\n")
            
            if result.get('error'):
                f.write(f"Error: {result['error']}\n")
                continue
                
            f.write(f"Compliance Status: {'✓ Compliant' if result['is_compliant'] else '✗ Non-compliant'}\n\n")
            
            if not result['is_compliant'] and 'issues' in result:
                f.write("Issues Found:\n")
                for issue in result['issues']:
                    f.write(f"- {issue['rule']}: {issue['description']}\n")
                    f.write(f"  Severity: {issue['severity']}\n")
            
            if 'metadata' in result:
                f.write("\nMetadata:\n")
                for key, value in result['metadata'].items():
                    f.write(f"- {key}: {'✓' if value else '✗'}\n")
            
            if 'structure' in result:
                f.write("\nStructure:\n")
                for key, value in result['structure'].items():
                    f.write(f"- {key}: {'✓' if value else '✗'}\n")
            
            if 'text' in result:
                f.write("\nText Accessibility:\n")
                for key, value in result['text'].items():
                    f.write(f"- {key}: {value}\n")
            
            f.write("\n" + "=" * 50 + "\n")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Check PDFs for 508 compliance')
    parser.add_argument('--dir', required=True, help='Directory containing PDFs to check')
    parser.add_argument('--report', default='accessibility_report.txt', help='Output report file')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run the checks
    checker = PDFAccessibilityChecker(args.dir)
    results = checker.check_directory()
    
    # Generate the report
    generate_report(results, args.report)
    print(f"\nAccessibility report generated: {args.report}") 
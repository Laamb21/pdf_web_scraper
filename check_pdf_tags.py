#!/usr/bin/env python3

import os
import csv
from PyPDF2 import PdfReader
from typing import List, Dict

def check_pdf_tagging(pdf_path: str) -> Dict:
    """Check if a PDF file has tagging."""
    try:
        with open(pdf_path, 'rb') as file:
            pdf = PdfReader(file)
            has_tags = '/StructTreeRoot' in pdf.trailer['/Root'] if '/Root' in pdf.trailer else False
            return {
                'filename': os.path.basename(pdf_path),
                'has_tags': has_tags,
                'page_count': len(pdf.pages)
            }
    except Exception as e:
        return {
            'filename': os.path.basename(pdf_path),
            'has_tags': False,
            'page_count': 0,
            'error': str(e)
        }

def process_directory(directory: str) -> List[Dict]:
    """Process all PDFs in the given directory."""
    results = []
    for filename in os.listdir(directory):
        if filename.lower().endswith('.pdf'):
            pdf_path = os.path.join(directory, filename)
            result = check_pdf_tagging(pdf_path)
            results.append(result)
    return results

def generate_csv_report(results: List[Dict], output_file: str):
    """Generate a CSV report of the results."""
    fieldnames = ['filename', 'has_tags', 'page_count', 'error']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(result)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Check PDFs for tagging')
    parser.add_argument('--dir', required=True, help='Directory containing PDFs to check')
    parser.add_argument('--output', default='pdf_tagging_report.csv', 
                       help='Output CSV file (default: pdf_tagging_report.csv)')
    
    args = parser.parse_args()
    
    print(f"Processing PDFs in {args.dir}...")
    results = process_directory(args.dir)
    generate_csv_report(results, args.output)
    print(f"\nReport generated: {args.output}")
    
    # Print summary
    total_pdfs = len(results)
    tagged_pdfs = sum(1 for r in results if r.get('has_tags', False))
    print(f"\nSummary:")
    print(f"Total PDFs processed: {total_pdfs}")
    print(f"PDFs with tags: {tagged_pdfs}")
    print(f"PDFs without tags: {total_pdfs - tagged_pdfs}")

if __name__ == "__main__":
    main()

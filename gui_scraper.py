#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
import time
import os
from urllib.parse import urlparse
import webbrowser
from pdf_scraper import PDFScraper

class PDFScraperGUI:
    """
    Tkinter GUI frontend for the PDF web scraper.
    Provides a user-friendly interface for configuring and running PDF scraping operations.
    """
    
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Web Scraper")
        self.root.geometry("800x700")
        self.root.minsize(600, 500)
        
        # Initialize variables
        self.scraper = None
        self.scraper_thread = None
        self.is_scraping = False
        self.start_time = None
        self.update_queue = queue.Queue()
        
        # Statistics tracking
        self.stats = {
            'pages_crawled': 0,
            'pages_found': 0,
            'pdfs_found': 0,
            'pdfs_downloaded': 0,
            'current_activity': 'Ready'
        }
        
        # Create GUI elements
        self.create_widgets()
        self.setup_styles()
        
        # Start the update loop
        self.root.after(100, self.process_queue)
    
    def create_widgets(self):
        """Create and layout all GUI widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # URL Input Section
        self.create_url_section(main_frame, 0)
        
        # Output Directory Section
        self.create_output_section(main_frame, 1)
        
        # Advanced Options Section
        self.create_advanced_section(main_frame, 2)
        
        # Progress Section
        self.create_progress_section(main_frame, 3)
        
        # Control Buttons
        self.create_control_section(main_frame, 4)
        
        # Results Section
        self.create_results_section(main_frame, 5)
    
    def create_url_section(self, parent, row):
        """Create URL input section."""
        url_frame = ttk.LabelFrame(parent, text="Website URL", padding="5")
        url_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        url_frame.columnconfigure(1, weight=1)
        
        ttk.Label(url_frame, text="URL:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, font=('TkDefaultFont', 10))
        self.url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        # URL validation indicator
        self.url_status = ttk.Label(url_frame, text="", foreground="gray")
        self.url_status.grid(row=0, column=2, sticky=tk.W)
        
        # Bind URL validation
        self.url_var.trace('w', self.validate_url)
    
    def create_output_section(self, parent, row):
        """Create output directory selection section."""
        output_frame = ttk.LabelFrame(parent, text="Output Directory", padding="5")
        output_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)
        
        ttk.Label(output_frame, text="Save to:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.output_var = tk.StringVar(value=os.path.join(os.getcwd(), "downloads"))
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_var, font=('TkDefaultFont', 10))
        self.output_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.browse_button = ttk.Button(output_frame, text="Browse", command=self.browse_directory)
        self.browse_button.grid(row=0, column=2, sticky=tk.W)
    
    def create_advanced_section(self, parent, row):
        """Create advanced options section."""
        self.advanced_frame = ttk.LabelFrame(parent, text="Advanced Options", padding="5")
        self.advanced_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.advanced_frame.columnconfigure(1, weight=1)
        
        # Max Crawl Depth
        ttk.Label(self.advanced_frame, text="Max Crawl Depth:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        depth_frame = ttk.Frame(self.advanced_frame)
        depth_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        self.depth_var = tk.StringVar(value="3")
        depth_options = [("1 level", "1"), ("2 levels", "2"), ("3 levels", "3"), 
                        ("5 levels", "5"), ("10 levels", "10"), ("Unlimited", "-1")]
        
        for i, (text, value) in enumerate(depth_options):
            rb = ttk.Radiobutton(depth_frame, text=text, variable=self.depth_var, value=value)
            rb.grid(row=0, column=i, sticky=tk.W, padx=(0, 10))
        
        # Timeout setting
        ttk.Label(self.advanced_frame, text="Timeout (seconds):").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        
        self.timeout_var = tk.StringVar(value="30")
        timeout_spin = ttk.Spinbox(self.advanced_frame, from_=5, to=300, textvariable=self.timeout_var, width=10)
        timeout_spin.grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        
        # SSL Verification
        self.ssl_var = tk.BooleanVar(value=True)
        ssl_check = ttk.Checkbutton(self.advanced_frame, text="Verify SSL certificates", variable=self.ssl_var)
        ssl_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
    
    def create_progress_section(self, parent, row):
        """Create progress tracking section."""
        progress_frame = ttk.LabelFrame(parent, text="Progress", padding="5")
        progress_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(1, weight=1)
        
        # Overall progress bar
        ttk.Label(progress_frame, text="Overall Progress:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.progress_label = ttk.Label(progress_frame, text="0%")
        self.progress_label.grid(row=0, column=2, sticky=tk.W)
        
        # Current activity
        ttk.Label(progress_frame, text="Status:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.activity_label = ttk.Label(progress_frame, text="Ready", foreground="blue")
        self.activity_label.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        # Statistics frame
        stats_frame = ttk.Frame(progress_frame)
        stats_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(3, weight=1)
        
        # Time tracking
        ttk.Label(stats_frame, text="Time Elapsed:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.time_elapsed_label = ttk.Label(stats_frame, text="00:00:00")
        self.time_elapsed_label.grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(stats_frame, text="ETA:").grid(row=0, column=2, sticky=tk.W, padx=(20, 10))
        self.eta_label = ttk.Label(stats_frame, text="--:--:--")
        self.eta_label.grid(row=0, column=3, sticky=tk.W)
        
        # Statistics
        ttk.Label(stats_frame, text="Pages Crawled:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.pages_label = ttk.Label(stats_frame, text="0 / 0")
        self.pages_label.grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        
        ttk.Label(stats_frame, text="PDFs Found:").grid(row=1, column=2, sticky=tk.W, padx=(20, 10), pady=(5, 0))
        self.pdfs_label = ttk.Label(stats_frame, text="0 / 0")
        self.pdfs_label.grid(row=1, column=3, sticky=tk.W, pady=(5, 0))
    
    def create_control_section(self, parent, row):
        """Create control buttons section."""
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=row, column=0, columnspan=2, pady=(0, 10))
        
        self.start_button = ttk.Button(control_frame, text="Start Scraping", command=self.start_scraping)
        self.start_button.grid(row=0, column=0, padx=(0, 10))
        
        self.stop_button = ttk.Button(control_frame, text="Stop", command=self.stop_scraping, state='disabled')
        self.stop_button.grid(row=0, column=1, padx=(0, 10))
        
        self.clear_button = ttk.Button(control_frame, text="Clear Results", command=self.clear_results)
        self.clear_button.grid(row=0, column=2, padx=(0, 10))
        
        self.open_folder_button = ttk.Button(control_frame, text="Open Download Folder", command=self.open_download_folder)
        self.open_folder_button.grid(row=0, column=3)
    
    def create_results_section(self, parent, row):
        """Create results display section."""
        results_frame = ttk.LabelFrame(parent, text="Results", padding="5")
        results_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        parent.rowconfigure(row, weight=1)
        
        # Results text area with scrollbar
        self.results_text = scrolledtext.ScrolledText(results_frame, height=10, wrap=tk.WORD)
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def setup_styles(self):
        """Configure custom styles for the GUI."""
        style = ttk.Style()
        
        # Configure colors for different message types
        self.results_text.tag_configure("success", foreground="green")
        self.results_text.tag_configure("error", foreground="red")
        self.results_text.tag_configure("warning", foreground="orange")
        self.results_text.tag_configure("info", foreground="blue")
    
    def validate_url(self, *args):
        """Validate the entered URL and update status indicator."""
        url = self.url_var.get().strip()
        if not url:
            self.url_status.config(text="", foreground="gray")
            return
        
        try:
            parsed = urlparse(url)
            if parsed.scheme in ('http', 'https') and parsed.netloc:
                self.url_status.config(text="✓", foreground="green")
            else:
                self.url_status.config(text="✗", foreground="red")
        except:
            self.url_status.config(text="✗", foreground="red")
    
    def browse_directory(self):
        """Open directory selection dialog."""
        directory = filedialog.askdirectory(initialdir=self.output_var.get())
        if directory:
            self.output_var.set(directory)
    
    def start_scraping(self):
        """Start the PDF scraping process."""
        # Validate inputs
        if not self.validate_inputs():
            return
        
        # Disable start button and enable stop button
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.is_scraping = True
        self.start_time = time.time()
        
        # Clear previous results
        self.clear_results()
        
        # Reset statistics
        self.stats = {
            'pages_crawled': 0,
            'pages_found': 0,
            'pdfs_found': 0,
            'pdfs_downloaded': 0,
            'current_activity': 'Initializing...'
        }
        
        # Create scraper instance
        max_depth = int(self.depth_var.get()) if self.depth_var.get() != "-1" else 999999
        
        self.scraper = EnhancedPDFScraper(
            base_url=self.url_var.get().strip(),
            output_dir=self.output_var.get(),
            timeout=int(self.timeout_var.get()),
            verify_ssl=self.ssl_var.get(),
            max_depth=max_depth,
            progress_callback=self.update_progress
        )
        
        # Start scraping in separate thread
        self.scraper_thread = threading.Thread(target=self.run_scraper, daemon=True)
        self.scraper_thread.start()
        
        self.log_message("Scraping started...", "info")
    
    def run_scraper(self):
        """Run the scraper in a separate thread."""
        try:
            self.scraper.crawl()
            self.update_queue.put(('finished', 'Scraping completed successfully!'))
        except Exception as e:
            self.update_queue.put(('error', f'Scraping failed: {str(e)}'))
    
    def stop_scraping(self):
        """Stop the current scraping operation."""
        if self.scraper:
            self.scraper.stop_scraping = True
        
        self.is_scraping = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        
        self.log_message("Scraping stopped by user.", "warning")
        self.activity_label.config(text="Stopped")
    
    def validate_inputs(self):
        """Validate user inputs before starting scraping."""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a website URL.")
            return False
        
        try:
            parsed = urlparse(url)
            if not (parsed.scheme in ('http', 'https') and parsed.netloc):
                messagebox.showerror("Error", "Please enter a valid HTTP or HTTPS URL.")
                return False
        except:
            messagebox.showerror("Error", "Please enter a valid URL.")
            return False
        
        output_dir = self.output_var.get()
        if not output_dir:
            messagebox.showerror("Error", "Please select an output directory.")
            return False
        
        try:
            os.makedirs(output_dir, exist_ok=True)
        except:
            messagebox.showerror("Error", "Cannot create or access the output directory.")
            return False
        
        return True
    
    def update_progress(self, update_type, data):
        """Callback function to receive progress updates from scraper."""
        self.update_queue.put((update_type, data))
    
    def process_queue(self):
        """Process updates from the scraper thread."""
        try:
            while True:
                update_type, data = self.update_queue.get_nowait()
                
                if update_type == 'stats':
                    self.stats.update(data)
                    self.update_display()
                elif update_type == 'log':
                    self.log_message(data['message'], data.get('level', 'info'))
                elif update_type == 'finished':
                    self.scraping_finished(data)
                elif update_type == 'error':
                    self.scraping_error(data)
                    
        except queue.Empty:
            pass
        
        # Update time display if scraping
        if self.is_scraping and self.start_time:
            self.update_time_display()
        
        # Schedule next update
        self.root.after(100, self.process_queue)
    
    def update_display(self):
        """Update the progress display with current statistics."""
        # Update progress bar (rough estimate based on pages crawled vs found)
        if self.stats['pages_found'] > 0:
            progress = min(100, (self.stats['pages_crawled'] / max(self.stats['pages_found'], 1)) * 100)
        else:
            progress = 0
        
        self.progress_var.set(progress)
        self.progress_label.config(text=f"{progress:.1f}%")
        
        # Update activity
        self.activity_label.config(text=self.stats['current_activity'])
        
        # Update statistics
        self.pages_label.config(text=f"{self.stats['pages_crawled']} / {self.stats['pages_found']}")
        self.pdfs_label.config(text=f"{self.stats['pdfs_downloaded']} / {self.stats['pdfs_found']}")
    
    def update_time_display(self):
        """Update elapsed time and ETA display."""
        if not self.start_time:
            return
        
        elapsed = time.time() - self.start_time
        elapsed_str = self.format_time(elapsed)
        self.time_elapsed_label.config(text=elapsed_str)
        
        # Calculate ETA based on current progress
        if self.stats['pages_crawled'] > 0 and self.stats['pages_found'] > 0:
            pages_remaining = max(0, self.stats['pages_found'] - self.stats['pages_crawled'])
            if pages_remaining > 0:
                rate = self.stats['pages_crawled'] / elapsed  # pages per second
                if rate > 0:
                    eta_seconds = pages_remaining / rate
                    eta_str = self.format_time(eta_seconds)
                    self.eta_label.config(text=eta_str)
                else:
                    self.eta_label.config(text="--:--:--")
            else:
                self.eta_label.config(text="00:00:00")
        else:
            self.eta_label.config(text="--:--:--")
    
    def format_time(self, seconds):
        """Format seconds into HH:MM:SS string."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def scraping_finished(self, message):
        """Handle scraping completion."""
        self.is_scraping = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        
        self.progress_var.set(100)
        self.progress_label.config(text="100%")
        self.activity_label.config(text="Completed")
        
        self.log_message(message, "success")
        
        # Show summary
        if self.scraper:
            summary = f"\nScraping Summary:\n"
            summary += f"Pages crawled: {len(self.scraper.visited_urls)}\n"
            summary += f"PDFs found: {len(self.scraper.found_pdfs)}\n"
            summary += f"PDFs downloaded: {len(self.scraper.downloaded_pdfs)}\n"
            summary += f"Failed downloads: {len(self.scraper.failed_downloads)}\n"
            self.log_message(summary, "info")
    
    def scraping_error(self, error_message):
        """Handle scraping errors."""
        self.is_scraping = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.activity_label.config(text="Error")
        
        self.log_message(f"Error: {error_message}", "error")
        messagebox.showerror("Scraping Error", error_message)
    
    def log_message(self, message, level="info"):
        """Add a message to the results log."""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.results_text.insert(tk.END, formatted_message, level)
        self.results_text.see(tk.END)
    
    def clear_results(self):
        """Clear the results display."""
        self.results_text.delete(1.0, tk.END)
        
        # Reset progress display
        self.progress_var.set(0)
        self.progress_label.config(text="0%")
        self.activity_label.config(text="Ready")
        self.time_elapsed_label.config(text="00:00:00")
        self.eta_label.config(text="--:--:--")
        self.pages_label.config(text="0 / 0")
        self.pdfs_label.config(text="0 / 0")
    
    def open_download_folder(self):
        """Open the download folder in the system file manager."""
        output_dir = self.output_var.get()
        if os.path.exists(output_dir):
            if os.name == 'nt':  # Windows
                os.startfile(output_dir)
            elif os.name == 'posix':  # macOS and Linux
                os.system(f'open "{output_dir}"' if os.uname().sysname == 'Darwin' else f'xdg-open "{output_dir}"')
        else:
            messagebox.showwarning("Warning", "Download folder does not exist yet.")


class EnhancedPDFScraper(PDFScraper):
    """Enhanced PDF scraper with GUI integration and improved PDF detection."""
    
    def __init__(self, base_url, output_dir="downloads", timeout=30, verify_ssl=True, max_depth=3, progress_callback=None):
        super().__init__(base_url, output_dir, timeout, verify_ssl, max_depth)
        self.progress_callback = progress_callback
        self.stop_scraping = False
        
    def crawl(self):
        """Enhanced crawl method with progress reporting."""
        from collections import deque
        
        # Queue of (url, depth) pairs to process
        queue = deque([(self.base_url, 0)])
        self.visited_urls.clear()
        self.found_pdfs.clear()
        
        while queue and not self.stop_scraping:
            current_url, depth = queue.popleft()
            
            # Skip if we've reached max depth or already visited
            if depth > self.max_depth or current_url in self.visited_urls:
                continue
            
            # Mark as visited
            self.visited_urls.add(current_url)
            
            # Report progress
            if self.progress_callback:
                self.progress_callback('stats', {
                    'pages_crawled': len(self.visited_urls),
                    'pages_found': len(self.visited_urls) + len(queue),
                    'pdfs_found': len(self.found_pdfs),
                    'pdfs_downloaded': len(self.downloaded_pdfs),
                    'current_activity': f'Crawling: {current_url[:50]}...'
                })
                
                self.progress_callback('log', {
                    'message': f'Crawling page: {current_url}',
                    'level': 'info'
                })
            
            try:
                # Check robots.txt before accessing
                if not self.can_fetch(current_url):
                    continue
                    
                # Fetch and parse the page
                response = self.session.get(current_url, timeout=self.timeout)
                response.raise_for_status()
                
                # Parse HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Enhanced PDF detection
                self.enhanced_pdf_detection(soup, current_url)
                
                # If we haven't reached max depth, add new links to queue
                if depth < self.max_depth:
                    new_links = self.extract_links(soup, current_url)
                    for link in new_links:
                        if link not in self.visited_urls:
                            queue.append((link, depth + 1))
                            
            except Exception as e:
                if self.progress_callback:
                    self.progress_callback('log', {
                        'message': f'Error processing {current_url}: {str(e)}',
                        'level': 'error'
                    })
                continue
        
        # Final progress update
        if self.progress_callback:
            self.progress_callback('stats', {
                'pages_crawled': len(self.visited_urls),
                'pages_found': len(self.visited_urls),
                'pdfs_found': len(self.found_pdfs),
                'pdfs_downloaded': len(self.downloaded_pdfs),
                'current_activity': 'Completed'
            })
    
    def enhanced_pdf_detection(self, soup, source_url):
        """Enhanced PDF detection supporting multiple embedding methods."""
        from urllib.parse import urljoin
        
        # Direct links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.lower().endswith('.pdf'):
                pdf_url = urljoin(source_url, href)
                self.process_pdf_url(pdf_url, source_url, 'direct link')
        
        # Embedded PDFs
        for embed in soup.find_all('embed', src=True):
            src = embed['src']
            if src.lower().endswith('.pdf') or 'pdf' in src.lower():
                pdf_url = urljoin(source_url, src)
                self.process_pdf_url(pdf_url, source_url, 'embed')
        
        # Object tags
        for obj in soup.find_all('object', data=True):
            data = obj['data']
            if data.lower().endswith('.pdf') or 'pdf' in data.lower():
                pdf_url = urljoin(source_url, data)
                self.process_pdf_url(pdf_url, source_url, 'object')
        
        # Iframe sources
        for iframe in soup.find_all('iframe', src=True):
            src = iframe['src']
            if src.lower().endswith('.pdf') or 'pdf' in src.lower():
                pdf_url = urljoin(source_url, src)
                self.process_pdf_url(pdf_url, source_url, 'iframe')
        
        # Cloud storage patterns (basic detection)
        for link in soup.find_all('a', href=True):
            href = link['href']
            if any(pattern in href.lower() for pattern in ['drive.google.com', 'dropbox.com', 'onedrive']):
                if 'pdf' in href.lower() or link.get_text().lower().endswith('.pdf'):
                    self.process_pdf_url(href, source_url, 'cloud storage')
    
    def process_pdf_url(self, pdf_url, source_url, detection_method):
        """Process a detected PDF URL."""
        if pdf_url not in self.found_pdfs:
            self.found_pdfs.add(pdf_url)
            
            if self.progress_callback:
                self.progress_callback('log', {
                    'message': f'Found PDF ({detection_method}): {pdf_url}',
                    'level': 'info'
                })
                
                self.progress_callback('stats', {
                    'pages_crawled': len(self.visited_urls),
                    'pages_found': len(self.visited_urls),
                    'pdfs_found': len(self.found_pdfs),
                    'pdfs_downloaded': len(self.downloaded_pdfs),
                    'current_activity': f'Downloading: {os.path.basename(pdf_url)}'
                })
            
            # Download the PDF
            result = self.download_pdf(pdf_url)
            if result and self.progress_callback:
                self.progress_callback('log', {
                    'message': f'Successfully downloaded: {os.path.basename(result)}',
                    'level': 'success'
                })


def main():
    """Main entry point for the GUI application."""
    root = tk.Tk()
    app = PDFScraperGUI(root)
    
    # Handle window closing
    def on_closing():
        if app.is_scraping:
            if messagebox.askokcancel("Quit", "Scraping is in progress. Do you want to quit?"):
                app.stop_scraping()
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()

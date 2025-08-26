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
        """Update the progress display with current statistics - FIXED PROGRESS BAR LOGIC."""
        # Debug logging for progress calculation
        crawled = self.stats['pages_crawled']
        found = self.stats['pages_found']
        
        # FIXED: Prevent 100% jump by ensuring proper initialization
        if crawled == 0 and found <= 1:
            progress = 0  # Always start at 0% until we actually start crawling
        elif found > 0:
            progress = min(100, (crawled / found) * 100)
        else:
            progress = 0
        
        # Debug logging for progress calculation
        self.log_message(f"DEBUG: Progress calculation - crawled: {crawled}, found: {found}, progress: {progress:.1f}%", "info")
        
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
    """Enhanced PDF scraper with GUI integration and massively improved PDF detection."""
    
    def __init__(self, base_url, output_dir="downloads", timeout=30, verify_ssl=True, max_depth=3, progress_callback=None):
        super().__init__(base_url, output_dir, timeout, verify_ssl, max_depth)
        self.progress_callback = progress_callback
        self.stop_scraping = False
        self.total_pages_discovered = 0
        
    def crawl(self):
        """Enhanced crawl method with FIXED progress reporting."""
        from collections import deque
        
        # Queue of (url, depth) pairs to process
        queue = deque([(self.base_url, 0)])
        self.visited_urls.clear()
        self.found_pdfs.clear()
        
        # FIXED: Initialize properly to prevent 100% jump
        self.total_pages_discovered = 0  # Start at 0
        
        # Initial progress report - FIXED to prevent 100% jump
        if self.progress_callback:
            self.progress_callback('stats', {
                'pages_crawled': 0,
                'pages_found': 0,  # Start at 0, will be updated as we discover pages
                'pdfs_found': 0,
                'pdfs_downloaded': 0,
                'current_activity': 'Starting crawl...'
            })
        
        while queue and not self.stop_scraping:
            current_url, depth = queue.popleft()
            
            # Skip if we've reached max depth or already visited
            if depth > self.max_depth or current_url in self.visited_urls:
                continue
            
            # Mark as visited
            self.visited_urls.add(current_url)
            
            # FIXED: Update total_pages_discovered BEFORE reporting progress
            if self.total_pages_discovered == 0:
                self.total_pages_discovered = 1  # Count the current page
            
            # Report progress with correct counts
            if self.progress_callback:
                self.progress_callback('stats', {
                    'pages_crawled': len(self.visited_urls),
                    'pages_found': max(self.total_pages_discovered, len(self.visited_urls)),  # Ensure found >= crawled
                    'pdfs_found': len(self.found_pdfs),
                    'pdfs_downloaded': len(self.downloaded_pdfs),
                    'current_activity': f'Crawling: {current_url[:50]}...'
                })
                
                self.progress_callback('log', {
                    'message': f'Crawling page ({len(self.visited_urls)}/{self.total_pages_discovered}): {current_url}',
                    'level': 'info'
                })
            
            try:
                # Check robots.txt before accessing
                if not self.can_fetch(current_url):
                    if self.progress_callback:
                        self.progress_callback('log', {
                            'message': f'Skipped by robots.txt: {current_url}',
                            'level': 'warning'
                        })
                    continue
                    
                # Fetch and parse the page
                response = self.session.get(current_url, timeout=self.timeout)
                response.raise_for_status()
                
                # Parse HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # MASSIVELY Enhanced PDF detection
                self.ultra_aggressive_pdf_detection(soup, current_url)
                
                # If we haven't reached max depth, add new links to queue
                if depth < self.max_depth:
                    new_links = self.extract_links(soup, current_url)
                    new_unique_links = 0
                    for link in new_links:
                        if link not in self.visited_urls and not any(url for url, _ in queue if url == link):
                            queue.append((link, depth + 1))
                            new_unique_links += 1
                    
                    # Update total discovered pages count
                    if new_unique_links > 0:
                        self.total_pages_discovered += new_unique_links
                        if self.progress_callback:
                            self.progress_callback('log', {
                                'message': f'Found {new_unique_links} new pages to crawl',
                                'level': 'info'
                            })
                            
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
                'pages_found': self.total_pages_discovered,
                'pdfs_found': len(self.found_pdfs),
                'pdfs_downloaded': len(self.downloaded_pdfs),
                'current_activity': 'Completed'
            })
    
    def ultra_aggressive_pdf_detection(self, soup, source_url):
        """MASSIVELY ENHANCED PDF detection - casts the widest possible net."""
        from urllib.parse import urljoin, urlparse, parse_qs
        import re
        
        # Collect all potential PDF URLs
        potential_pdfs = []
        
        # 1. Direct links ending with .pdf (highest priority)
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.lower().endswith('.pdf') or href.lower().endswith('.pdf?'):
                pdf_url = urljoin(source_url, href)
                potential_pdfs.append((pdf_url, 'direct link (.pdf)', link.get_text().strip(), 'high'))
        
        # 2. EXPANDED Shortened URL detection
        shortened_url_patterns = [
            'bit.ly/', 'tinyurl.com/', 't.co/', 'goo.gl/', 'ow.ly/', 'short.link/',
            'aptg.co/', 'rebrand.ly/', 'cutt.ly/', 'is.gd/', 'buff.ly/', 'ift.tt/',
            'tiny.cc/', 'lnkd.in/', 'fb.me/', 'amzn.to/', 'youtu.be/', 'git.io/',
            'short.ly/', 'trib.al/', 'shar.es/', 'po.st/', 'qr.ae/', 'v.gd/'
        ]
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            link_text = link.get_text().strip().lower()
            
            # Skip if already found as direct PDF
            if href.lower().endswith('.pdf'):
                continue
            
            # Check for shortened URLs
            if any(pattern in href.lower() for pattern in shortened_url_patterns):
                # MASSIVELY EXPANDED text analysis for shortened URLs
                pdf_keywords = [
                    'handbook', 'manual', 'guide', 'document', 'report', 'brochure',
                    'catalog', 'specification', 'datasheet', 'whitepaper', 'policy',
                    'instructions', 'procedures', 'guidelines', 'standards', 'forms',
                    'application', 'enrollment', 'registration', 'student', 'faculty',
                    'staff', 'employee', 'code', 'conduct', 'rules', 'regulations',
                    'syllabus', 'curriculum', 'schedule', 'calendar', 'newsletter',
                    'announcement', 'notice', 'memo', 'letter', 'contract', 'agreement'
                ]
                
                # Check if link text suggests it might be a PDF
                text_suggests_pdf = any(keyword in link_text for keyword in pdf_keywords)
                
                # Also check surrounding context (parent elements)
                context_text = ""
                parent = link.parent
                if parent:
                    context_text = parent.get_text().lower()
                
                context_suggests_pdf = any(keyword in context_text for keyword in pdf_keywords)
                
                if text_suggests_pdf or context_suggests_pdf:
                    pdf_url = urljoin(source_url, href)
                    potential_pdfs.append((pdf_url, 'shortened URL with PDF context', link_text, 'medium'))
                    if self.progress_callback:
                        self.progress_callback('log', {
                            'message': f'🔗 Detected shortened URL with PDF context: {href} - "{link_text}"',
                            'level': 'info'
                        })
        
        # 3. ULTRA ENHANCED Cloud Storage and CDN Detection
        for link in soup.find_all('a', href=True):
            href = link['href']
            link_text = link.get_text().strip()
            
            # Skip if already found
            if href.lower().endswith('.pdf') or any(href == url for url, _, _, _ in potential_pdfs):
                continue
            
            # AWS S3 and CloudFront (ULTRA EXPANDED)
            if any(pattern in href.lower() for pattern in [
                's3.amazonaws.com', '.s3.', 'amazonaws.com', 'cloudfront.net',
                'core-docs.s3.amazonaws.com', 's3-us-west-', 's3-us-east-',
                's3-eu-west-', 's3-ap-southeast-', 's3.us-west-', 's3.us-east-',
                's3.eu-west-', 's3.ap-southeast-', 'awsstatic.com', 'aws.amazon.com',
                'cloudfront.com', 'd1.awsstatic.com', 'd2.awsstatic.com'
            ]):
                # Be ultra aggressive with S3 URLs - check for any document indicators
                is_likely_document = any(indicator in href.lower() or indicator in link_text.lower() 
                                       for indicator in ['doc', 'file', 'upload', 'document', 'pdf', 
                                                       'report', 'manual', 'guide', 'handbook'])
                priority = 'high' if is_likely_document else 'medium'
                potential_pdfs.append((href, 'AWS S3/CloudFront', link_text, priority))
                if self.progress_callback:
                    self.progress_callback('log', {
                        'message': f'☁️ Found AWS S3/CloudFront URL ({priority}): {href}',
                        'level': 'info'
                    })
            
            # Google Drive patterns (ULTRA EXPANDED)
            elif any(pattern in href.lower() for pattern in [
                'drive.google.com/file/d/', 'drive.google.com/open?id=',
                'docs.google.com/document/d/', 'drive.google.com/uc?id=',
                'drive.google.com/uc?export=download', 'drive.google.com/drive/folders',
                'drive.google.com/drive/u/', 'drive.google.com/folderview?id=',
                'googledrive.com/host/', 'googleusercontent.com', 'drive.google.com/viewerng/viewer',
                'docs.google.com/viewer?url=', 'drive.google.com/a/', 'sites.google.com/site/',
                'sites.google.com/view/', 'drive.google.com/thumbnail?id='
            ]):
                # Enhanced Google Drive detection with URL transformation
                transformed_url = self.transform_google_drive_url(href)
                final_url = transformed_url if transformed_url != href else href
                potential_pdfs.append((final_url, 'Google Drive (Enhanced)', link_text, 'high'))
                if self.progress_callback:
                    self.progress_callback('log', {
                        'message': f'📁 Found Google Drive URL: {href}' + (f' → {final_url}' if transformed_url != href else ''),
                        'level': 'info'
                    })
            
            # Dropbox patterns (ULTRA EXPANDED)
            elif any(pattern in href.lower() for pattern in [
                'dropbox.com/s/', 'dropbox.com/sh/', 'dl.dropboxusercontent.com',
                'dropbox.com/scl/fi/', 'dropbox.com/scl/fo/', 'dropbox.com/l/',
                'db.tt/', 'dropbox.com/home/', 'dropbox.com/work/',
                'dropboxusercontent.com', 'dropbox.com/preview/', 'dropbox.com/paper/doc/'
            ]):
                # Transform Dropbox URLs for direct download
                transformed_url = self.transform_dropbox_url(href)
                final_url = transformed_url if transformed_url != href else href
                potential_pdfs.append((final_url, 'Dropbox (Enhanced)', link_text, 'high'))
                if self.progress_callback:
                    self.progress_callback('log', {
                        'message': f'📦 Found Dropbox URL: {href}' + (f' → {final_url}' if transformed_url != href else ''),
                        'level': 'info'
                    })
            
            # OneDrive patterns (ULTRA EXPANDED)
            elif any(pattern in href.lower() for pattern in [
                'onedrive.live.com', '1drv.ms/', 'sharepoint.com',
                'office.com/wd/hub', 'outlook.office365.com', 'onedrive.com',
                'sharepoint-df.com', 'officeapps.live.com', 'office365.com',
                'microsoftonline.com', 'sharepoint.microsoft.com', 'live.com/redir'
            ]):
                # Transform OneDrive URLs for direct download
                transformed_url = self.transform_onedrive_url(href)
                final_url = transformed_url if transformed_url != href else href
                potential_pdfs.append((final_url, 'OneDrive/SharePoint (Enhanced)', link_text, 'high'))
                if self.progress_callback:
                    self.progress_callback('log', {
                        'message': f'☁️ Found OneDrive/SharePoint URL: {href}' + (f' → {final_url}' if transformed_url != href else ''),
                        'level': 'info'
                    })
            
            # Box patterns (EXPANDED)
            elif any(pattern in href.lower() for pattern in [
                'box.com/s/', 'app.box.com/file/', 'box.com/shared/',
                'box.com/v/', 'account.box.com/login', 'box.net/shared/',
                'box.com/embed/', 'box.com/embed_widget/'
            ]):
                potential_pdfs.append((href, 'Box (Enhanced)', link_text, 'high'))
                if self.progress_callback:
                    self.progress_callback('log', {
                        'message': f'📁 Found Box URL: {href}',
                        'level': 'info'
                    })
            
            # iCloud Drive patterns (NEW)
            elif any(pattern in href.lower() for pattern in [
                'icloud.com/iclouddrive/', 'icloud.com/pages/', 'icloud.com/numbers/',
                'icloud.com/keynote/', 'icloud.com/attachment/'
            ]):
                potential_pdfs.append((href, 'iCloud Drive', link_text, 'medium'))
                if self.progress_callback:
                    self.progress_callback('log', {
                        'message': f'☁️ Found iCloud Drive URL: {href}',
                        'level': 'info'
                    })
            
            # WeTransfer patterns (NEW)
            elif any(pattern in href.lower() for pattern in [
                'wetransfer.com/downloads/', 'we.tl/', 'wetransfer.com/dl/'
            ]):
                potential_pdfs.append((href, 'WeTransfer', link_text, 'medium'))
                if self.progress_callback:
                    self.progress_callback('log', {
                        'message': f'📤 Found WeTransfer URL: {href}',
                        'level': 'info'
                    })
            
            # MediaFire patterns (NEW)
            elif any(pattern in href.lower() for pattern in [
                'mediafire.com/file/', 'mediafire.com/download/', 'mediafire.com/?'
            ]):
                potential_pdfs.append((href, 'MediaFire', link_text, 'medium'))
                if self.progress_callback:
                    self.progress_callback('log', {
                        'message': f'🔥 Found MediaFire URL: {href}',
                        'level': 'info'
                    })
            
            # Mega patterns (NEW)
            elif any(pattern in href.lower() for pattern in [
                'mega.nz/file/', 'mega.co.nz/file/', 'mega.nz/#!', 'mega.co.nz/#!'
            ]):
                potential_pdfs.append((href, 'Mega', link_text, 'medium'))
                if self.progress_callback:
                    self.progress_callback('log', {
                        'message': f'🔒 Found Mega URL: {href}',
                        'level': 'info'
                    })
            
            # Apptegy CDN (specific to test website) - Enhanced
            elif any(pattern in href.lower() for pattern in [
                'cmsv2-assets.apptegy.net', 'apptegy.net', 'apptegy.com'
            ]):
                # Check if it might be a document
                is_likely_document = any(word in href.lower() or word in link_text.lower() 
                                       for word in ['doc', 'file', 'upload', 'document', 'pdf', 
                                                  'report', 'manual', 'guide', 'handbook'])
                if is_likely_document:
                    potential_pdfs.append((href, 'Apptegy CDN', link_text, 'medium'))
                    if self.progress_callback:
                        self.progress_callback('log', {
                            'message': f'📄 Found Apptegy CDN document URL: {href}',
                            'level': 'info'
                        })
            
            # Generic CDN patterns (NEW)
            elif any(pattern in href.lower() for pattern in [
                'cdn.', 'assets.', 'static.', 'files.', 'docs.', 'downloads.',
                'media.', 'content.', 'resources.'
            ]) and any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx']):
                potential_pdfs.append((href, 'Generic CDN', link_text, 'medium'))
                if self.progress_callback:
                    self.progress_callback('log', {
                        'message': f'🌐 Found Generic CDN document URL: {href}',
                        'level': 'info'
                    })
        
        # 4. ULTRA AGGRESSIVE Text-Based Detection
        for link in soup.find_all('a', href=True):
            href = link['href']
            link_text = link.get_text().strip().lower()
            
            # Skip if already processed
            if any(href == url for url, _, _, _ in potential_pdfs):
                continue
            
            # MASSIVELY EXPANDED keyword lists
            ultra_strong_indicators = [
                'pdf', '.pdf', 'download pdf', 'view pdf', 'open pdf',
                'pdf document', 'pdf file', 'pdf report', 'pdf manual'
            ]
            
            strong_indicators = [
                'download', 'document', 'report', 'manual', 'guide', 'handbook',
                'brochure', 'catalog', 'specification', 'datasheet', 'whitepaper',
                'policy', 'procedures', 'guidelines', 'standards', 'forms',
                'application', 'enrollment', 'registration', 'syllabus',
                'curriculum', 'schedule', 'calendar', 'newsletter'
            ]
            
            medium_indicators = [
                'student handbook', 'faculty handbook', 'employee handbook',
                'code of conduct', 'annual report', 'financial report',
                'safety manual', 'user guide', 'instruction manual',
                'technical specification', 'product catalog', 'course catalog',
                'academic calendar', 'school calendar', 'event schedule',
                'meeting minutes', 'board minutes', 'policy document',
                'compliance document', 'audit report', 'assessment report'
            ]
            
            # Check for ultra strong indicators
            if any(indicator in link_text for indicator in ultra_strong_indicators):
                pdf_url = urljoin(source_url, href)
                potential_pdfs.append((pdf_url, 'ultra strong text indicator', link_text, 'high'))
            
            # Check for strong indicators
            elif any(indicator in link_text for indicator in strong_indicators):
                pdf_url = urljoin(source_url, href)
                potential_pdfs.append((pdf_url, 'strong text indicator', link_text, 'high'))
            
            # Check for medium indicators
            elif any(indicator in link_text for indicator in medium_indicators):
                pdf_url = urljoin(source_url, href)
                potential_pdfs.append((pdf_url, 'medium text indicator', link_text, 'medium'))
        
        # 5. URL Pattern Analysis (EXPANDED)
        for link in soup.find_all('a', href=True):
            href = link['href']
            link_text = link.get_text().strip().lower()
            
            # Skip if already processed
            if any(href == url for url, _, _, _ in potential_pdfs):
                continue
            
            try:
                parsed_url = urlparse(href)
                params = parse_qs(parsed_url.query)
                
                # Check for PDF-related parameters (EXPANDED)
                pdf_params = ['format', 'type', 'export', 'output', 'download', 'file', 'doc', 'document']
                for param in pdf_params:
                    if param in params:
                        param_values = [v.lower() for v in params[param]]
                        if any('pdf' in val for val in param_values):
                            pdf_url = urljoin(source_url, href)
                            potential_pdfs.append((pdf_url, 'URL parameter PDF', link_text, 'medium'))
                            break
                
                # Check for file extension in path (EXPANDED)
                if any(ext in parsed_url.path.lower() for ext in ['.pdf', '.doc', '.docx']):
                    pdf_url = urljoin(source_url, href)
                    potential_pdfs.append((pdf_url, 'document in path', link_text, 'high'))
                    
            except Exception:
                pass
        
        # 6. Embedded content detection (EXPANDED)
        for embed in soup.find_all('embed', src=True):
            src = embed['src']
            if any(ext in src.lower() for ext in ['.pdf', '.doc', '.docx']):
                pdf_url = urljoin(source_url, src)
                potential_pdfs.append((pdf_url, 'embed tag', '', 'high'))
        
        # 7. Object tags (EXPANDED)
        for obj in soup.find_all('object', data=True):
            data = obj['data']
            if any(ext in data.lower() for ext in ['.pdf', '.doc', '.docx']):
                pdf_url = urljoin(source_url, data)
                potential_pdfs.append((pdf_url, 'object tag', '', 'high'))
        
        # 8. Iframe sources (EXPANDED)
        for iframe in soup.find_all('iframe', src=True):
            src = iframe['src']
            if any(ext in src.lower() for ext in ['.pdf', '.doc', '.docx']):
                pdf_url = urljoin(source_url, src)
                potential_pdfs.append((pdf_url, 'iframe', '', 'high'))
        
        # 9. JavaScript and data attributes (EXPANDED)
        for element in soup.find_all(attrs={'onclick': True}):
            onclick = element.get('onclick', '').lower()
            if any(ext in onclick for ext in ['.pdf', '.doc', '.docx']):
                # Try to extract URL from onclick
                url_match = re.search(r'["\']([^"\']*\.(?:pdf|doc|docx)[^"\']*)["\']', onclick)
                if url_match:
                    pdf_url = urljoin(source_url, url_match.group(1))
                    potential_pdfs.append((pdf_url, 'JavaScript onclick', element.get_text().strip(), 'medium'))
        
        # Check data attributes (EXPANDED)
        for element in soup.find_all(attrs=lambda x: x and any(attr.startswith('data-') for attr in x)):
            for attr, value in element.attrs.items():
                if attr.startswith('data-') and isinstance(value, str):
                    if any(ext in value.lower() for ext in ['.pdf', '.doc', '.docx']) or (attr.endswith('-url') and 'pdf' in value.lower()):
                        pdf_url = urljoin(source_url, value)
                        potential_pdfs.append((pdf_url, f'data attribute ({attr})', element.get_text().strip(), 'medium'))
        
        # 10. NEW: Try Everything Mode - Check ALL links for potential PDFs
        for link in soup.find_all('a', href=True):
            href = link['href']
            link_text = link.get_text().strip()
            
            # Skip if already processed or is obviously not a document
            if any(href == url for url, _, _, _ in potential_pdfs):
                continue
            
            # Skip obvious non-documents
            skip_patterns = ['javascript:', 'mailto:', 'tel:', '#', 'facebook.com', 'twitter.com', 'instagram.com']
            if any(pattern in href.lower() for pattern in skip_patterns):
                continue
            
            # If the link has any text that could suggest a document, try it
            if len(link_text) > 3 and any(char.isalpha() for char in link_text):
                pdf_url = urljoin(source_url, href)
                potential_pdfs.append((pdf_url, 'try everything mode', link_text, 'low'))
        
        # Sort by priority and process
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        potential_pdfs.sort(key=lambda x: priority_order.get(x[3], 3))
        
        # Process all potential PDFs
        for pdf_url, detection_method, link_text, priority in potential_pdfs:
            self.process_pdf_url(pdf_url, source_url, detection_method, link_text, priority)
    
    def transform_google_drive_url(self, url):
        """Transform Google Drive URLs to direct download format."""
        import re
        from urllib.parse import parse_qs, urlparse
        
        try:
            # Extract file ID from various Google Drive URL formats
            file_id = None
            
            # Format: https://drive.google.com/file/d/FILE_ID/view
            match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
            if match:
                file_id = match.group(1)
            
            # Format: https://drive.google.com/open?id=FILE_ID
            elif 'open?id=' in url:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                if 'id' in params:
                    file_id = params['id'][0]
            
            # Format: https://drive.google.com/uc?id=FILE_ID
            elif 'uc?id=' in url:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                if 'id' in params:
                    file_id = params['id'][0]
            
            # If we found a file ID, create direct download URL
            if file_id:
                return f"https://drive.google.com/uc?export=download&id={file_id}"
            
        except Exception as e:
            if self.progress_callback:
                self.progress_callback('log', {
                    'message': f'Error transforming Google Drive URL: {str(e)}',
                    'level': 'warning'
                })
        
        return url  # Return original URL if transformation fails
    
    def transform_dropbox_url(self, url):
        """Transform Dropbox URLs to direct download format."""
        try:
            # Convert Dropbox share URLs to direct download
            if 'dropbox.com/s/' in url or 'dropbox.com/sh/' in url:
                # Replace ?dl=0 with ?dl=1 for direct download
                if '?dl=0' in url:
                    return url.replace('?dl=0', '?dl=1')
                elif '?dl=' not in url:
                    # Add direct download parameter
                    separator = '&' if '?' in url else '?'
                    return f"{url}{separator}dl=1"
            
            # Handle dropbox.com/scl/fi/ URLs
            elif 'dropbox.com/scl/fi/' in url:
                if '?dl=0' in url:
                    return url.replace('?dl=0', '?dl=1')
                elif 'dl=' not in url:
                    separator = '&' if '?' in url else '?'
                    return f"{url}{separator}dl=1"
                    
        except Exception as e:
            if self.progress_callback:
                self.progress_callback('log', {
                    'message': f'Error transforming Dropbox URL: {str(e)}',
                    'level': 'warning'
                })
        
        return url  # Return original URL if transformation fails
    
    def transform_onedrive_url(self, url):
        """Transform OneDrive URLs to direct download format."""
        try:
            # Handle 1drv.ms short URLs - these usually redirect properly
            if '1drv.ms/' in url:
                return url  # Let the redirect handling take care of this
            
            # Handle onedrive.live.com URLs
            elif 'onedrive.live.com' in url:
                # Try to convert to direct download format
                if 'redir?resid=' in url:
                    # Add download parameter
                    separator = '&' if '?' in url else '?'
                    return f"{url}{separator}authkey=!&download=1"
                elif 'view.aspx' in url:
                    # Replace view with download
                    return url.replace('view.aspx', 'download.aspx')
            
            # Handle SharePoint URLs
            elif 'sharepoint.com' in url:
                # SharePoint URLs often work as-is, but we can try to add download parameter
                if 'download=1' not in url:
                    separator = '&' if '?' in url else '?'
                    return f"{url}{separator}download=1"
                    
        except Exception as e:
            if self.progress_callback:
                self.progress_callback('log', {
                    'message': f'Error transforming OneDrive URL: {str(e)}',
                    'level': 'warning'
                })
        
        return url  # Return original URL if transformation fails
    
    def process_pdf_url(self, pdf_url, source_url, detection_method, link_text="", priority="medium"):
        """Process a detected PDF URL with enhanced content-type verification and redirect following."""
        if pdf_url in self.found_pdfs:
            return
            
        # Add to found PDFs immediately to avoid duplicates
        self.found_pdfs.add(pdf_url)
        
        if self.progress_callback:
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")
            self.progress_callback('log', {
                'message': f'{priority_emoji} Found potential PDF ({detection_method}): {pdf_url}' + (f' - "{link_text}"' if link_text else ''),
                'level': 'info'
            })
        
        # Determine if content-type verification is needed
        is_confirmed_pdf = pdf_url.lower().endswith('.pdf') or pdf_url.lower().endswith('.pdf?')
        needs_verification = not is_confirmed_pdf
        
        # Enhanced content-type verification with redirect following
        if needs_verification:
            try:
                # Make a HEAD request to check content type and follow redirects
                if self.progress_callback:
                    self.progress_callback('log', {
                        'message': f'Verifying content-type for: {pdf_url}',
                        'level': 'info'
                    })
                
                head_response = self.session.head(pdf_url, timeout=self.timeout, allow_redirects=True)
                final_url = head_response.url
                content_type = head_response.headers.get('content-type', '').lower()
                content_disposition = head_response.headers.get('content-disposition', '').lower()
                
                # Log redirect information for shortened URLs
                if final_url != pdf_url:
                    if self.progress_callback:
                        self.progress_callback('log', {
                            'message': f'🔄 Redirect detected: {pdf_url} → {final_url}',
                            'level': 'info'
                        })
                    
                    # Check if final URL is a PDF
                    if final_url.lower().endswith('.pdf') or final_url.lower().endswith('.pdf?'):
                        is_confirmed_pdf = True
                        if self.progress_callback:
                            self.progress_callback('log', {
                                'message': f'✅ Redirect leads to PDF: {final_url}',
                                'level': 'success'
                            })
                
                # Check for PDF indicators in headers
                pdf_indicators = ['pdf', 'application/pdf', 'application/x-pdf']
                is_pdf_content = any(indicator in content_type for indicator in pdf_indicators)
                is_pdf_disposition = 'pdf' in content_disposition
                
                # Check for download indicators
                is_download = any(indicator in content_disposition for indicator in ['attachment', 'filename'])
                
                if is_pdf_content or is_pdf_disposition:
                    is_confirmed_pdf = True
                    if self.progress_callback:
                        self.progress_callback('log', {
                            'message': f'✅ Confirmed PDF by headers: {content_type}',
                            'level': 'success'
                        })
                elif is_download and priority in ['medium', 'high']:
                    # If it's a download but we can't confirm it's PDF, try anyway for medium/high priority
                    is_confirmed_pdf = True
                    if self.progress_callback:
                        self.progress_callback('log', {
                            'message': f'⚠️ Download detected, attempting anyway: {content_type}',
                            'level': 'warning'
                        })
                elif detection_method in ['shortened URL with PDF context', 'AWS S3/CloudFront']:
                    # For shortened URLs and cloud storage, be more aggressive
                    is_confirmed_pdf = True
                    if self.progress_callback:
                        self.progress_callback('log', {
                            'message': f'⚠️ {detection_method}, attempting download',
                            'level': 'warning'
                        })
                else:
                    if self.progress_callback:
                        self.progress_callback('log', {
                            'message': f'❌ Not a PDF (content-type: {content_type}): {pdf_url}',
                            'level': 'warning'
                        })
                    return
                    
            except Exception as e:
                if self.progress_callback:
                    self.progress_callback('log', {
                        'message': f'⚠️ Could not verify content-type for {pdf_url}: {str(e)}',
                        'level': 'warning'
                    })
                
                # Decision logic based on priority and detection method
                if priority == 'high' or detection_method in ['direct link (.pdf)', 'embed tag', 'object tag', 'iframe']:
                    # High confidence sources - proceed anyway
                    is_confirmed_pdf = True
                elif priority == 'medium' and any(cloud in detection_method for cloud in ['Google Drive', 'Dropbox', 'OneDrive', 'Box', 'AWS S3', 'shortened URL', 'CloudFront']):
                    # Cloud storage and shortened URLs - likely to be valid
                    is_confirmed_pdf = True
                else:
                    # Low confidence - skip
                    if self.progress_callback:
                        self.progress_callback('log', {
                            'message': f'❌ Skipping unverifiable link: {pdf_url}',
                            'level': 'warning'
                        })
                    return
        
        # Proceed with download if confirmed
        if is_confirmed_pdf:
            # Update progress before downloading
            if self.progress_callback:
                self.progress_callback('stats', {
                    'pages_crawled': len(self.visited_urls),
                    'pages_found': self.total_pages_discovered,
                    'pdfs_found': len(self.found_pdfs),
                    'pdfs_downloaded': len(self.downloaded_pdfs),
                    'current_activity': f'Downloading: {os.path.basename(pdf_url)}'
                })
            
            # Download the PDF
            result = self.download_pdf(pdf_url)
            if result and self.progress_callback:
                self.progress_callback('log', {
                    'message': f'✅ Successfully downloaded: {os.path.basename(result)}',
                    'level': 'success'
                })
                
                # Update download count
                self.progress_callback('stats', {
                    'pages_crawled': len(self.visited_urls),
                    'pages_found': self.total_pages_discovered,
                    'pdfs_found': len(self.found_pdfs),
                    'pdfs_downloaded': len(self.downloaded_pdfs),
                    'current_activity': f'Downloaded: {os.path.basename(result)}'
                })
        else:
            if self.progress_callback:
                self.progress_callback('log', {
                    'message': f'❌ Skipping unconfirmed PDF: {pdf_url}',
                    'level': 'warning'
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

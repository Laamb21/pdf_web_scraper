# PDF Web Scraper GUI

A user-friendly tkinter GUI frontend for the PDF web scraper application.

## Features

- **Easy-to-use Interface**: Simple GUI for configuring and running PDF scraping operations
- **Enhanced PDF Detection**: Finds PDFs through multiple methods:
  - Direct links (`<a href="*.pdf">`)
  - Embedded PDFs (`<embed src="*.pdf">`)
  - Object tags (`<object data="*.pdf">`)
  - Iframe sources (`<iframe src="*.pdf">`)
  - Cloud storage links (Google Drive, Dropbox, OneDrive)
- **Flexible Crawl Depth**: Choose from 1 level to unlimited depth
- **Real-time Progress Tracking**: 
  - Live progress bar and statistics
  - Time elapsed and estimated time remaining
  - Current activity status
  - Pages crawled and PDFs found/downloaded
- **Advanced Options**:
  - Configurable timeout settings
  - SSL certificate verification toggle
  - Custom output directory selection
- **Results Management**:
  - Detailed logging with color-coded messages
  - Summary statistics
  - Quick access to download folder

## Installation

1. Ensure you have Python 3.7+ installed
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Starting the GUI

Run the GUI application:
```bash
python gui_scraper.py
```

### Using the Interface

1. **Enter Website URL**: Input the starting URL to scrape PDFs from
2. **Select Output Directory**: Choose where to save downloaded PDFs (defaults to `downloads/`)
3. **Configure Advanced Options** (optional):
   - **Max Crawl Depth**: Select how deep to crawl the website
     - 1 level: Only the starting page
     - 2-10 levels: Crawl to specified depth
     - Unlimited: Crawl all reachable pages (use with caution)
   - **Timeout**: Set request timeout in seconds (5-300)
   - **SSL Verification**: Enable/disable SSL certificate verification
4. **Start Scraping**: Click "Start Scraping" to begin the process
5. **Monitor Progress**: Watch real-time updates in the progress section
6. **View Results**: Check the results log for detailed information about found and downloaded PDFs

### Control Options

- **Start Scraping**: Begin the PDF scraping process
- **Stop**: Halt the current scraping operation
- **Clear Results**: Clear the results log and reset progress
- **Open Download Folder**: Open the output directory in your file manager

## Progress Tracking

The GUI provides comprehensive progress tracking:

- **Overall Progress Bar**: Visual indicator of completion
- **Time Elapsed**: Shows how long the scraping has been running
- **Estimated Time Remaining**: Calculated based on current crawling rate
- **Pages Crawled**: Number of pages processed vs. total found
- **PDFs Found/Downloaded**: Count of PDFs discovered and successfully downloaded
- **Current Activity**: Real-time status of what the scraper is doing

## Enhanced PDF Detection

The GUI version includes enhanced PDF detection that goes beyond simple link crawling:

### Detection Methods

1. **Direct Links**: Traditional `<a href="document.pdf">` links
2. **Embedded PDFs**: PDFs embedded using `<embed>` tags
3. **Object Tags**: PDFs displayed through `<object>` elements
4. **Iframe Sources**: PDFs loaded in iframes
5. **Cloud Storage**: Basic detection of PDF links from:
   - Google Drive
   - Dropbox
   - OneDrive

### Smart Crawling

- **Robots.txt Compliance**: Respects website crawling rules
- **Rate Limiting**: Built-in delays to avoid overwhelming servers
- **Domain Restriction**: Only crawls pages within the same domain
- **Duplicate Prevention**: Avoids re-downloading the same PDFs

## Error Handling

The GUI includes robust error handling:

- **Input Validation**: Checks URLs and directory paths before starting
- **Network Error Recovery**: Handles connection issues gracefully
- **SSL Certificate Issues**: Option to disable verification for problematic sites
- **User-friendly Messages**: Clear error descriptions with suggested solutions

## Tips for Best Results

1. **Start Small**: Begin with a low crawl depth (1-2 levels) to test the website
2. **Check Robots.txt**: Ensure the website allows crawling
3. **Monitor Progress**: Use the stop button if the scraping takes too long
4. **SSL Issues**: If you encounter SSL errors, try disabling SSL verification
5. **Large Sites**: For unlimited depth, be prepared for long run times

## Troubleshooting

### Common Issues

**GUI Won't Start**
- Ensure Python 3.7+ is installed
- Check that all dependencies are installed: `pip install -r requirements.txt`

**SSL Certificate Errors**
- Try disabling "Verify SSL certificates" in Advanced Options
- Some websites have valid but unverifiable certificates

**No PDFs Found**
- Check if the website actually contains PDFs
- Try increasing the crawl depth
- Some PDFs may be behind authentication or JavaScript

**Slow Performance**
- Large websites can take significant time to crawl
- Consider reducing the crawl depth
- Use the stop button if needed

## Command Line Alternative

The original command-line interface is still available in `pdf_scraper.py`:

```bash
python pdf_scraper.py --url https://example.com --output-dir downloads --max-depth 3
```

## License

This project is licensed under the same terms as the original PDF scraper.

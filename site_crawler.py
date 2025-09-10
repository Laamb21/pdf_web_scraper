# site_crawler.py 

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def crawl_site(start_url):
    '''
    Crawl all pages of a website starting from the start_url.
    Prints each link found along with its content type.
    '''

    visited = set()                         # To avoid duplicates 
    to_visit = [start_url]                  # Start with given URL
    domain = urlparse(start_url).netloc     # Extract domain
    total_links = 0                         # Counter for total links found

    while to_visit:
        url = to_visit.pop(0)      # Get next URL
        if url in visited:
            continue
        visited.add(url)

        try:
            response = requests.get(url, timeout=5, stream=True)
            content_type = response.headers.get("Content-Type", "").split(";")[0]
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            continue

        # Increment total links count 
        total_links += 1

        # Decide what to print based on content type 
        if content_type == "text/html":
            print(f"Found HTML page: {url}")
            # Parse links inside HTML pages only
            try:
                soup = BeautifulSoup(response.text, "html.parser")
                for link in soup.find_all("a", href=True):
                    new_url = urljoin(url, link["href"]) # Handle relative URLs
                    # Stay within the same domain
                    if urlparse(new_url).netloc == domain and new_url not in visited:
                        to_visit.append(new_url)
            except Exception as e:
                print(f"Failed to parse HTML at {url}: {e}")

        elif content_type == "application/pdf":
            print(f"Found PDF: {url}")
        elif content_type in ["application/msword", "application/vnd/openxmlformats-officedocument.wordprocessingml.document"]:
            print(f"Found Word document: {url}")
        elif content_type in ["application/vnd.ms-excel, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
            print(f"Found Excel file: {url}")
        elif content_type in ["application/vnd.ms-powerpoint", "application/vnd.openxmlformats-officedocument.presentationml.presentation"]:
            print(f"Found PowerPoint file: {url}")
        elif content_type.startswith("image/"):
            print(f"Found Image ({content_type}): {url}")
        elif content_type.startswith("video/"):
            print(f"Found Video ({content_type}): {url}")
        elif content_type.startswith("audio/"):
            print(f"Found Audio ({content_type}): {url}")
        elif content_type in ["application/json"]:
            print(f"Found JSON data: {url}")
        elif content_type in ["application/xml", "text/xml"]:
            print(f"Found XML data: {url}")
        elif content_type in ["application/javascript", "text/javascript"]:
            print(f"Found JavaScript file: {url}")
        elif content_type == "text/css":
            print(f"Found CSS file: {url}")
        elif content_type in ["application/zip", "application/x-tar", "application/gzip"]:
            print(f"Found Archive: ({content_type}): {url}")
        elif content_type == "application/octet-stream":
            print(f"Found Binary file: {url}")
        else:
            print(f"Found Other ({content_type}): {url}")

    print(f"\n Crawl finished. Total links found: {total_links}")

if __name__ == "__main__":
    website = input("Enter a website URL (e.g. https://example.com): ").strip()
    crawl_site(website)
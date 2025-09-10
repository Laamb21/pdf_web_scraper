# site_crawler.py 

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def crawl_site(start_url):
    '''
    Crawl all pages of a website starting from the start_url.
    Prints each URL found.
    '''

    visited = set()         # To avoid duplicates
    to_visit = [start_url]  # Start with the given URL

    # Extract the domain (so we don't wander into other sites)
    domain = urlparse(start_url).netloc

    while to_visit:
        url = to_visit.pop(0)   # Get the next URL
        if url in visited: 
            continue
        visited.add(url)

        try:
            response = requests.get(url, timeout=5)
            # Only crawl HTML pages
            if "text/html" not in response.headers.get("Content-Type", ""):
                continue
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")

        print("Found: ", url)

        # Parse the page and find all links
        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.find_all("a", href=True):
            new_url = urljoin(url, link["href"]) # Handle relative URLs
            # Stay within the same domain
            if urlparse(new_url).netloc == domain and new_url not in visited:
                to_visit.append(new_url)

if __name__ == "__main__":
    website = input ("Enter a website URL (e.g. https://example.com): ").strip()
    crawl_site(website)
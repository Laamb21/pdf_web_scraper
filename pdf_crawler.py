# pdf_crawler.py 

import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from collections import deque 

# ----------------- Configuration -----------------
GET_TIMEOUT = 10
CRAWL_DELAY_SEC = 0.1   # polite pause between requests
USER_AGENT = "PDFCrawler" 
MAX_PAGES = 9999
VERIFY_BATCH_DELAY = 0.0  # delay between HEAD verifications
# -------------------------------------------------

PDF_EXT_REGEX = re.compile(r"\.pdf($|[?#])", re.IGNORECASE)
INLINE_PDF_REGEX = re.compile(r"https?://[^\s\"'<>]+\.pdf(?:[^\s\"'<>]*)?", re.IGNORECASE)

# Heuristics: common viewer/storage hosts & patterns
VIEWER_HOST_HINTS = [
    "drive.google.com", "docs.google.com", "sites.google.com",
    "onedrive.live.com", "sharepoint.com", "box.com", "dropbox.com"
]
VIEWER_PATH_HINTS = [
    "/viewer", "pdfjs", "/embed", "/preview", "/view", "render"
]

def is_html(response):
    ctype = response.headers.get("Content-Type", "").split(";")[0].lower()
    return ctype in ("text/html", "application/xhtml+xml")

def looks_like_pdf_url(url: str) -> bool:
    # Obvious: ends with .pdf (allow query/fragment)
    if PDF_EXT_REGEX.search(url):
        return True
    # Query params that often carry a PDF 
    parsed = urlparse(url)
    q = parse_qs(parsed.query)
    for key in ("file", "url", "resource", "src", "document"):
        for v in q.get(key, []):
            if PDF_EXT_REGEX.search(v or ""):
                return True
    # Known viewer hosts or paths often wrap PDFs
    if any(h in parsed.netloc.lower() for h in VIEWER_HOST_HINTS):
        return True
    if any(h in parsed.path.lower() for h in VIEWER_PATH_HINTS):
        return True
    return False

def same_site(url, base_url, allow_subdomains=True):
    def root(host):
        host = host.lower()
        return host[4:] if host.startswith("www.") else host
    nu = root(urlparse(url).netloc)
    nb = root(urlparse(base_url).netloc)
    if not allow_subdomains:
        return nu == nb
    return (nu == nb ) or nu.endswith("." + nb)
    
def head_is_pdf(session: requests.Session, url: str) -> bool:
    try:
        r = session.head(url, allow_redirects=True, timeout=10)
        ctype = r.headers.get("Content-Type", "").split(";")[0].lower()
        return ctype == "application/pdf"
    except requests.RequestException:
        return False
    
def normalize(url: str) -> str:
    # Strip default fragments line #view=Fit
    parsed = urlparse(url)
    return parsed._replace(fragment="").geturl()

def crawl_pdfs(start_url: str):
    start_url = start_url.strip()
    parsed_start = urlparse(start_url)
    if not parsed_start.scheme:
        start_url = "https://" + start_url

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    to_visit = deque([start_url])
    visited_pages = set()
    found_pdf_candidates = set()    # all PDF-looking URLs (may include viewers)
    pages_crawled = 0
    
    # ---------- Phase 1: fast crawl to collect candidates ----------
    while to_visit and pages_crawled < MAX_PAGES:
        page_url = to_visit.popleft()
        if page_url in visited_pages:
            continue
        visited_pages.add(page_url)

        # Fetch page
        try:
            resp = session.get(page_url, timeout=GET_TIMEOUT)
        except requests.RequestException as e:
            print(f"Page fetch failed: {page_url} ({e})")
            continue

        pages_crawled += 1
        if not is_html(resp):
            # Not HTML: no need to verify here - just move on quickly
            continue

        # Parse links from HTML
        soup = BeautifulSoup(resp.text, "html.parser")

        # Collect candidate URLs from href/src/data attributes
        candidates = set()

        # Anchor tags
        for a in soup.find_all("a", href=True):
            candidates.add(urljoin(page_url, a["href"]))

        # Embeds / iframes / object 
        for tag, attr in (("iframe", "src"), ("embed", "src"), ("object", "data")):
            for t in soup.find_all(tag):
                val = t.get(attr)
                if val:
                    candidates.add(urljoin(page_url, val))

        # Link rel=... 
        for l in soup.find_all("link", href=True):
            candidates.add(urljoin(page_url, l["href"]))

        # Inline ".pdf" URLs in page page or scripts/styles
        for m in INLINE_PDF_REGEX.findall(resp.text or ""):
            candidates.add(m)

        # Queue HTML pages from the same site; collect PDF-looking URLs globally
        for url in candidates:
            url = normalize(url)
            if same_site(url, start_url) and url not in visited_pages:
                to_visit.append(url)
            if looks_like_pdf_url(url):
                found_pdf_candidates.add(url)
                
        time.sleep(CRAWL_DELAY_SEC)
    
    # --------- Phase 2: verify which candidates are actual PDFs ----------
    verified_pdfs = set()
    for url in sorted(found_pdf_candidates):
        if PDF_EXT_REGEX.search(url):
            # Strong signal: endswith .pdf -> accept
            verified_pdfs.add(url)
            print(f"Found PDF (link): {url}")
        else:
            # Check viewer/share link by HEAD
            if head_is_pdf(session, url):
                verified_pdfs.add(url)
                print(f"Found PDF (verified): {url}")
        if VERIFY_BATCH_DELAY:
            time.sleep(VERIFY_BATCH_DELAY)

    # Summary 
    print("\nCrawl finished.")
    print(f"- Pages crawled: {len(visited_pages)} (cap {MAX_PAGES})")
    print(f"- PDF candidates seen: {len(found_pdf_candidates)}")
    print(f"- PDFs verified: {len(verified_pdfs)}")

    return sorted(verified_pdfs)

if __name__ == "__main__":
    start = input("Enter a website URL (e.g. https://example.com): ").strip()
    crawl_pdfs(start)
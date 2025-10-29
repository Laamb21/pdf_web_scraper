# pdf_crawler.py 

import re
import time
import sys
import os
import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from collections import deque, defaultdict

# ----------------- Configuration -----------------
GET_TIMEOUT = 10
HEAD_TIMEOUT = 10
CRAWL_DELAY_SEC = 0.15   # polite pause between requests
VERIFY_BATCH_DELAY = 0.0  # delay between HEAD verifications
USER_AGENT = "PDFCrawler" 
MAX_PAGES = 9999
ALLOW_SUBDOMAINS = True
# -------------------------------------------------

# Regexes & Heuristics
PDF_EXT_REGEX = re.compile(r"\.pdf($|[?#])", re.IGNORECASE)
INLINE_PDF_REGEX = re.compile(r"https?://[^\s\"'<>]+\.pdf(?:[^\s\"'<>]*)?", re.IGNORECASE)

VIEWER_HOST_HINTS = [
    "drive.google.com", "docs.google.com", "sites.google.com",
    "onedrive.live.com", "sharepoint.com", "box.com", "dropbox.com"
]
VIEWER_PATH_HINTS = [
    "/viewer", "pdfjs", "/embed", "/preview", "/view", "render"
]

DRIVE_FILE_RE = re.compile(r"https?://(?:drive|docs)\.google\.com/file/d/([^/]+)/", re.IGNORECASE)

# -------------------- Helpers --------------------
def is_html(response) -> bool:
    ctype = response.headers.get("Content-Type", "").split(";")[0].lower()
    return ctype in ("text/html", "application/xhtml+xml")

def normalize(url: str) -> str:
    # Strip default fragments line #view=Fit
    parsed = urlparse(url)
    return parsed._replace(fragment="").geturl()

def same_site(url: str, base_url: str, allow_subdomains: bool = True) -> bool:
    def root(h: str) -> str:
        h = h.lower()
        return h[4:] if h.startswith("www.") else h
    
    nu = root(urlparse(url).netloc)
    nb = root(urlparse(base_url).netloc)
    if not allow_subdomains:
        return nu == nb
    return (nu == nb) or nu.endswith("." + nb)

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
    
def head_is_pdf(session: requests.Session, url: str) -> tuple[bool, str, int]:
    # Head check for PDF; returns (is_pdf, content_type, status_code)
    try:
        r = session.head(url, allow_redirects=True, timeout=HEAD_TIMEOUT)
        ctype = (r.headers.get("Content-Type") or "").split(";")[0].lower()
        return (ctype == "application/pdf", ctype, r.status_code)
    except requests.RequestException:
        return (False, "", 0)
    
def get_is_pdf(session: requests.Session, url: str) -> tuple[bool, str, int]:
    '''
    Fallback when HEAD is blocked or inaccurate (common on Google Drive).
    USes a lightweight GET (stream=True) to read headers only
    '''
    try:
        r = session.get(url, allow_redirects=True, timeout=GET_TIMEOUT, stream=True)
        ctype = (r.headers.get("Content-Type") or "").split(";")[0].lower()
        return (ctype == "application/pdf", ctype, r.status_code)
    except requests.RequestException:
        return (False, "", 0)
    
def is_drive_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return host.endswith("drive.google.com") or host.endswith("docs.google.com")

def resolve_drive_redirect(url: str) -> str | None:
    '''
    Convert a Google Drive viewer/link to a direct download URL if possible.
    - /file/d/<ID>/view?... -> uc?export=download&id=<ID>[&resourcekey=...]
    - old 'open?id=' style -> uc?export=download&id=<ID>
    Preserves resourcekey because sometimes Google Drive requires it
    '''
    m = DRIVE_FILE_RE.match(url)
    if m:
        file_id = m.group(1)
        q = parse_qs(urlparse(url).query)
        resourcekey = q.get("resourcekey", [None])[0]
        base = f"htts://drive.google.com/uc?export=download&id={file_id}"
        return f"{base}&resourcekey={resourcekey}" if resourcekey else base
    
    parsed = urlparse(url)
    q = parse_qs(parsed.query)
    file_id = (q.get("id") or q.get("docid") or [None])[0]
    if file_id:
        resourcekey = q.get("resourcekey", [None])[0]
        base = f"https://drive.google.com/uc?export=download&id={file_id}"
        return f"{base}&resourcekey={resourcekey}" if resourcekey else base
    
    return None

# -------------------- Core --------------------
def crawl_pdfs(start_url: str, export_path: str | None = None):
    '''
    Crawl a site for PDFs (including Google Drive viewer links).
    - Phase 1: crawl same-site HTML pages and collect PDF candidates 
    - Phase 2: verify candidates (extensions, Drive resolver, HEAD/GET)
    - Phase 3: export results to Excel (verified_pdfs + candidates_seen)
    '''
    start_url = start_url.strip()
    parsed_start = urlparse(start_url)
    if not parsed_start.scheme:
        start_url = "https://" + start_url

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    to_visit = deque([start_url])
    visited_pages = set()

    # candidates_seen: url -> {reasons:set, found_on_pages: set}
    candidates_seen: dict[str, dict] = defaultdict(lambda: {"reasons": set(), "found_on_pages": set()})

    pages_crawled = 0
    
    # ---------- Phase 1: fast crawl to collect candidates ----------
    while to_visit and pages_crawled < MAX_PAGES:
        page_url = to_visit.popleft()
        page_url = normalize(page_url)
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
            candidates.add(("anchor", urljoin(page_url, a["href"])))

        # Embeds / iframes / object 
        for tag, attr in (("iframe", "src"), ("embed", "src"), ("object", "data")):
            for t in soup.find_all(tag):
                val = t.get(attr)
                if val:
                    candidates.add((tag, urljoin(page_url, val)))

        # Link rel=... (stylesheets, alternates, sometimes resources)
        for l in soup.find_all("link", href=True):
            candidates.add(("link", urljoin(page_url, l["href"])))

        # Inline strings that look like ...pdf
        for m in INLINE_PDF_REGEX.findall(resp.text or ""):
            candidates.add(("inline", m))

        # Process candidates: queue HTML pages (same site), collect PDF-looking URLs
        for reason, url in candidates:
            url = normalize(url)

            # Keep exploring same-site pages
            if same_site(url, start_url, allow_subdomains=ALLOW_SUBDOMAINS) and url not in visited_pages:
                to_visit.append(url)

            # Collect anything that looks like a PDF (extension, viewer hints, etc.)
            if looks_like_pdf_url(url):
                rec = candidates_seen[url]
                rec["reasons"].add(reason)
                rec["found_on_pages"].add(page_url)
                
        time.sleep(CRAWL_DELAY_SEC)
    
    # --------- Phase 2: verify which candidates are actual PDFs ----------
    verified_rows = []  # for Excel sheet 'verified_pdfs'
    for cand_url, meta in sorted(candidates_seen.items(), key=lambda kv: kv[0]):
        reasons = ",".join(sorted(meta["reasons"]))
        found_on = "; ".join(sorted(meta["found_on_pages"]))

        # Case A: direct *.pdf - accept immediately
        if PDF_EXT_REGEX.search(cand_url):
            verified_rows.append({
                "pdf_url": cand_url,
                "found_via": "extension",
                "source_url": cand_url,
                "found_on_page": found_on.split("; ")[0] if found_on else "",
                "http_status": "",       # not checked
                "content_type": ""       # not checked    
            })
            print(f"Found PDF (link): {cand_url}")
            if VERIFY_BATCH_DELAY:
                time.sleep(VERIFY_BATCH_DELAY)
            continue

        # Case B: Google Drive viewer/share link
        final_url = None
        http_status = 0
        content_type = ""
        if is_drive_url(cand_url):
            direct = resolve_drive_redirect(cand_url)
            if direct:
                ispdf, ctype, code = head_is_pdf(session, direct)
                if not ispdf:
                    ispdf, ctype, code = get_is_pdf(session, direct)
                if ispdf:
                    final_url, http_status, content_type = direct, code, ctype
            # If still not verified, try the original viewer URL just in case
            if not final_url:
                ispdf, ctype, code = head_is_pdf(session, cand_url)
                if not ispdf:
                    ispdf, ctype, code = get_is_pdf(session, cand_url)
                if ispdf:
                    final_url, http_status, content_type = cand_url, code, ctype

            if final_url:
                verified_rows.append({
                    "pdf_url": final_url, 
                    "found_via": "google_drive_resolved" if final_url != cand_url else "google_drive_viewer",
                    "source_url": cand_url,
                    "found_on_page": found_on.split("; ")[0] if found_on else "",
                    "http_status": http_status,
                    "content_type": content_type
                })
                print(f"Found PDF (Google Drive): {final_url} [via {cand_url}]")
                if VERIFY_BATCH_DELAY:
                    time.sleep(VERIFY_BATCH_DELAY)
                continue
        else:
            # Case C: other viewer/share links - try HEAD then GET
            ispdf, ctype, code = head_is_pdf(session, cand_url)
            if not ispdf:
                ispdf, ctype, code = get_is_pdf(session, cand_url)
            if ispdf:
                verified_rows.append({
                    "pdf_url": cand_url,
                    "found_via": "verified_head/get",
                    "source_url": cand_url,
                    "found_on_page": found_on.split("; ")[0] if found_on else "",
                    "http_status": code,
                    "content_type": ctype
                })
                print(f"Found PDF (verified): {cand_url}")
                if VERIFY_BATCH_DELAY:
                    time.sleep(VERIFY_BATCH_DELAY)
                continue

        # If we get here, the candidate stays unverified; we'll still export it in candidates sheet

    # ------------------- Build Excel export -------------------
    try:
        import pandas as pd     # requires pandas + openpyxl for .xlsx
        verified_df = pd.DataFrame(verified_rows, columns=[
            "pdf_url", "found_via", "found_on_page", "source_url", "http_status", "content_type"
        ])
        
        # Flatten candidates_seen for export
        cand_rows = []
        for url, meta in sorted(candidates_seen.items(), key=lambda kv: kv[0]):
            cand_rows.append({
                "candidate_url": url,
                "reasons": ",".join(sorted(meta["reasons"])),
                "found_on_pages": "; ".join(sorted(meta["found_on_pages"])),
                "was_verified": "yes" if any(row["pdf_url"] == url or row["source_url"] == url for row in verified_rows) else "no"
            }) 
        candidates_df = pd.DataFrame(cand_rows, columns=[
            "candidate_url", "reasons", "found_on_pages", "was_verified"
        ])

        # Default export path
        if not export_path:
            host = urlparse(start_url).netloc or "site"
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = f"pdf_crawl_{host}_{ts}.xlsx"
        
        with pd.ExcelWriter(export_path, engine="openpyxl") as writer:
            verified_df.to_excel(writer, sheet_name="verified_pdfs", index=False)
            candidates_df.to_excel(writer, sheet_name="candidates_seen", index=False)
        
        print("\n Crawl finished.")
        print(f"- Pages crawled: {len(visited_pages)} (cap {MAX_PAGES})")
        print(f"- PDF candidates seen: {len(candidates_seen)}")
        print(f"- PDFs verified: {len(verified_rows)}")
        print(f"- Excel export: {os.path.abspath(export_path)}")

    except ImportError:
        # Fallback: print summary if pandas/openpyxl not installed
        print("\n Crawl finished.")
        print(f"- Pages crawled: {len(visited_pages)} (cap {MAX_PAGES})")
        print(f"- PDF candidates seen: {len(candidates_seen)}")
        print(f"- PDFs verified: {len(verified_rows)}")
        print("- Verified URLS:")
        for r in verified_rows:
            print(" ", r["pdf_url"])

    return [r["pdf_url"] for r in verified_rows]

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        start = sys.argv[1]
        out = sys.argv[2] if len(sys.argv) >= 3 else None
    else:
        start = input("Enter a website URL (e.g., https://example.com): ").strip()
        out = None
    crawl_pdfs(start, export_path=out)
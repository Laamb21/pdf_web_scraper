#!/usr/bin/env python3

import ssl
import certifi
import urllib.request

# Set up SSL context with certifi
ssl_context = ssl.create_default_context(cafile=certifi.where())
https_handler = urllib.request.HTTPSHandler(context=ssl_context)
opener = urllib.request.build_opener(https_handler)
urllib.request.install_opener(opener)

import argparse
import sys
from urllib.robotparser import RobotFileParser
from urllib.error import URLError

def check_robots(site_url, path="/"):
    robots_url = site_url.rstrip("/") + "/robots.txt"
    print(f"[DEBUG] robots.txt URL → {robots_url}")

    rp = RobotFileParser()
    rp.set_url(robots_url)

    try:
        rp.read()
        print("[DEBUG] robots.txt downloaded & parsed")
    except URLError as e:
        print(f"[ERROR] failed to fetch robots.txt: {e}")
        return None, ""

    print(f"[DEBUG] disallow_all = {rp.disallow_all}")
    print(f"[DEBUG] allow_all    = {rp.allow_all}")

    full_path = site_url.rstrip("/") + path
    allowed = rp.can_fetch("*", full_path)
    return allowed, f"can_fetch('*', '{path}') == {allowed}"

def main():
    parser = argparse.ArgumentParser(
        description="Check robots.txt for scraping rules."
    )
    parser.add_argument("--site", required=True, help="e.g. https://example.com")
    parser.add_argument("--path", default="/", help="which path to check")
    args = parser.parse_args()

    result, message = check_robots(args.site, args.path)
    if result is None:
        sys.exit(1)
    print(message)

if __name__ == "__main__":
    main()

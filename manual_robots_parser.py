import requests

robots_url = "https://www.stoughtonschools.org".rstrip("/") + "/robots.txt"
print("Fetching:", robots_url)
resp = requests.get(robots_url, timeout=10)

print("Status code:", resp.status_code)
print("Contents:\n", resp.text)

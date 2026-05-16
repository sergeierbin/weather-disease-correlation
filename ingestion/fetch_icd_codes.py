# Fetches ICD-10 codes from the WHO ICD API and loads them into raw.icd_codes.
# WHO API docs: https://icd.who.int/icdapi
# Authentication: OAuth 2.0 client credentials (ICD_CLIENT_ID + ICD_CLIENT_SECRET from .env)
# Traversal: BFS over the ICD-10 hierarchy starting from the root entity.

import os
import sys
import time
import logging
import requests
from collections import deque  # Used for BFS queue (efficient popleft)

# Allow imports from the ingestion/ package root (e.g. utils.db)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.db import get_connection, execute_values

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── WHO API constants ─────────────────────────────────────────────────────────

TOKEN_URL = "https://icdaccessmanagement.who.int/connect/token"
# ICD-10 2019 release root — change the year to target a different release
API_ROOT  = "https://id.who.int/icd/release/10/2019"

# Headers required by every WHO ICD API request
BASE_HEADERS = {
    "Accept":          "application/json",  # Return JSON, not HTML
    "API-Version":     "v2",                # Stable API version
    "Accept-Language": "en",                # Return labels in English
}

# ── Authentication ────────────────────────────────────────────────────────────

def get_token():
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id":     os.environ["ICD_CLIENT_ID"],
            "client_secret": os.environ["ICD_CLIENT_SECRET"],
            "scope":         "icdapi_access",       # Required scope for the ICD API
            "grant_type":    "client_credentials",  # Machine-to-machine OAuth flow
        },
        timeout=30,
    )
    resp.raise_for_status()  # Raise immediately on wrong credentials (4xx)
    token = resp.json()["access_token"]
    log.info("WHO API token obtained")
    return token


def auth_headers(token):
    # Merge base headers with the Bearer token for each request
    return {**BASE_HEADERS, "Authorization": f"Bearer {token}"}

# ── API helpers ───────────────────────────────────────────────────────────────

def fetch_entity(url, token, retries=3):
    """Fetch a single ICD-10 entity by URL, with simple retry on 5xx errors."""
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=auth_headers(token), timeout=30)
            if resp.status_code == 401:
                # Token expired mid-run (WHO tokens last ~1 hour) — refresh and retry
                log.warning("Token expired, refreshing…")
                token = get_token()
                resp = requests.get(url, headers=auth_headers(token), timeout=30)
            resp.raise_for_status()
            return resp.json(), token
        except requests.RequestException as exc:
            if attempt == retries:
                raise  # Give up after all retries exhausted
            log.warning("Attempt %d failed (%s), retrying…", attempt, exc)
            time.sleep(2 ** attempt)  # Wait 2s, 4s, 8s between retries


def parse_entity(data, parent_url):
    """
    Extract (code, title, description, parent_code) from a WHO API response.
    Some fields are missing for intermediate/chapter nodes — default to None.
    """
    code      = data.get("code")         # None for chapter nodes (e.g. "I", "II")
    title_obj = data.get("title", {})
    title     = title_obj.get("@value")  # WHO wraps text values in {"@value": "..."}

    # `definition` is an optional longer description — not present on all nodes
    def_obj     = data.get("definition", {})
    description = def_obj.get("@value") if isinstance(def_obj, dict) else None

    # Derive parent_code from the last segment of the parent URL (e.g. ".../A00" → "A00")
    parent_code = parent_url.rstrip("/").split("/")[-1] if parent_url else None
    # Discard purely numeric segments — they are release year identifiers, not codes
    if parent_code and not any(c.isalpha() for c in parent_code):
        parent_code = None

    return code, title, description, parent_code

# ── BFS traversal ─────────────────────────────────────────────────────────────

def collect_all_codes(token):
    """
    Breadth-first traversal of the ICD-10 hierarchy.
    Returns a list of (code, title, description, parent_code) tuples.
    """
    rows    = []
    visited = set()                        # Prevent re-fetching the same URL
    queue   = deque([(API_ROOT, None)])    # Start from root; root has no parent

    while queue:
        url, parent_url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        data, token = fetch_entity(url, token)
        code, title, description, parent_code = parse_entity(data, parent_url)

        # Only store nodes that carry a code (skip bare chapter containers)
        if code:
            rows.append((code, title, description, parent_code))
            if len(rows) % 500 == 0:
                log.info("Collected %d codes so far…", len(rows))

        # Each entity lists URLs of its direct children — enqueue them
        for child_url in data.get("child", []):
            if child_url not in visited:
                queue.append((child_url, url))  # Pass current URL as parent

    log.info("Traversal complete — %d codes collected", len(rows))
    return rows

# ── Database load ─────────────────────────────────────────────────────────────

# ON CONFLICT DO UPDATE makes this safe to re-run — existing rows are refreshed,
# not duplicated, so the script is fully idempotent.
INSERT_SQL = """
    INSERT INTO raw.icd_codes (code, title, description, parent_code)
    VALUES %s
    ON CONFLICT (code) DO UPDATE SET
        title       = EXCLUDED.title,
        description = EXCLUDED.description,
        parent_code = EXCLUDED.parent_code,
        loaded_at   = NOW()
"""

def load_to_db(rows):
    conn = get_connection()
    try:
        execute_values(conn, INSERT_SQL, rows)  # Single-batch insert for all rows
        log.info("Loaded %d rows into raw.icd_codes", len(rows))
    finally:
        conn.close()  # Always close, even if execute_values raises

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    token = get_token()
    rows  = collect_all_codes(token)
    if not rows:
        log.warning("No codes collected — check API credentials and connectivity")
        return
    load_to_db(rows)

if __name__ == "__main__":
    main()

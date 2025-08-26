#!/usr/bin/env python3
import os, re, json, time, pathlib, itertools, requests, http.client, urllib.parse
from urllib.parse import quote_plus, urlsplit, urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed

COOKIE_HEADER = os.environ["COOKIE_HEADER"]
REQUEST_TIMEOUT = 30
PAUSE_BETWEEN_REQUESTS = 0.1
MAX_DOWNLOAD_WORKERS = 5

item_uuid_re = re.compile(r'https://exampapers\.ed\.ac\.uk/server/api/core/items/([0-9a-f-]+)/bundles"')
bundle_uuid_re = re.compile(r'https://exampapers\.ed\.ac\.uk/server/api/core/bundles/([0-9a-f-]+)/bitstreams')
bit_uuid_re = re.compile(r'https://exampapers\.ed\.ac\.uk/server/api/core/bitstreams/([0-9a-f-]+)/bundle')
name_re = re.compile(r'"name"\s*:\s*"([^"]+)"')

def make_session():
    s = requests.Session()
    s.headers.update({"Cookie": COOKIE_HEADER, "Accept": "application/json, text/plain, */*", "User-Agent": "exam-scraper/1.3"})
    retries = Retry(total=5, connect=5, read=5, backoff_factor=0.5, status_forcelist=[429,500,502,503,504], allowed_methods=frozenset(["GET"]), raise_on_status=False)
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s

def fetch_text(session, url):
    r = session.get(url, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.text

def sanitize_filename(name):
    name = name.strip().replace("\0", "")
    name = re.sub(r'[\/:*?"<>|]+', "_", name)
    name = re.sub(r"\s+", " ", name)
    return (name[:200].strip() or "unnamed")

def ensure_dir(p):
    pathlib.Path(p).mkdir(parents=True, exist_ok=True)

def download_with_cookie_only(url, out_path, cookie_header, max_redirects=5, timeout=60):
    redirects = 0
    while True:
        parts = urlsplit(url)
        conn_cls = http.client.HTTPSConnection if parts.scheme == "https" else http.client.HTTPConnection
        port = parts.port or (443 if parts.scheme == "https" else 80)
        path = parts.path + (("?" + parts.query) if parts.query else "")
        conn = conn_cls(parts.hostname, port, timeout=timeout)
        try:
            conn.request("GET", path, headers={"Cookie": cookie_header})
            resp = conn.getresponse()
            if resp.status in (301, 302, 303, 307, 308):
                if redirects >= max_redirects:
                    raise RuntimeError("Too many redirects.")
                location = resp.getheader("Location")
                if not location:
                    raise RuntimeError("Redirect without Location header.")
                url = urljoin(url, location)
                redirects += 1
                conn.close()
                continue
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status} {resp.reason}")
            with open(out_path, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            return
        finally:
            conn.close()

def dedupe(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x); out.append(x)
    return out

def progress(step_label, done, total):
    pct = int(done * 100 / total) if total else 100
    print(f"\r{step_label}: {pct}% completed", end="", flush=True)

def main():
    print("Enter Course ID (e.g., MATH08058): ", end="", flush=True)
    course_id = input().strip()
    if not course_id:
        print("No Course ID provided."); return
    query = quote_plus(course_id)
    initial_url = f"https://exampapers.ed.ac.uk/server/api/discover/search/objects?sort=dc.date.accessioned,DESC&page=0&size=9999&query={query}&embed=thumbnail&embed=item%2Fthumbnail"

    session = make_session()

    base_dir = pathlib.Path(__file__).resolve().parent
    stamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = f"{sanitize_filename(course_id)}_{stamp}"
    download_dir = base_dir / folder_name
    ensure_dir(download_dir)

    initial_text = fetch_text(session, initial_url)
    time.sleep(PAUSE_BETWEEN_REQUESTS)

    item_uuids = dedupe(item_uuid_re.findall(initial_text))

    # step 1: process item UUIDs -> fetch bundles
    bundles_by_item = {}
    skipped_bundles_no_original = 0
    step1_total = len(item_uuids)
    step1_done = 0
    print()
    for item_uuid in item_uuids:
        url = f"https://exampapers.ed.ac.uk/server/api/core/items/{item_uuid}/bundles"
        text = fetch_text(session, url)
        time.sleep(PAUSE_BETWEEN_REQUESTS)
        bundle_uuids = dedupe(bundle_uuid_re.findall(text))
        bundles_by_item[item_uuid] = bundle_uuids
        step1_done += 1
        progress("Step 1/4", step1_done, step1_total)
    print()

    all_bundles = [(item_uuid, b) for item_uuid, bs in bundles_by_item.items() for b in bs]

    # step 2: fetch bitstreams JSON for each bundle (UUID2)
    bundle_texts = {}
    step2_total = len(all_bundles)
    step2_done = 0
    for _, bundle_uuid in all_bundles:
        url = f"https://exampapers.ed.ac.uk/server/api/core/bundles/{bundle_uuid}/bitstreams"
        text = fetch_text(session, url)
        time.sleep(PAUSE_BETWEEN_REQUESTS)
        bundle_texts[bundle_uuid] = text
        step2_done += 1
        progress("Step 2/4", step2_done, step2_total)
    print()

    # step 3: extract UUID3 + names; skip bundles without ORIGINAL
    bitstreams_by_bundle = {}
    step3_total = len(all_bundles)
    step3_done = 0
    for _, bundle_uuid in all_bundles:
        text = bundle_texts[bundle_uuid]

        if "ORIGINAL" not in text:
            skipped_bundles_no_original += 1
            bitstreams_by_bundle[bundle_uuid] = []
            step3_done += 1
            progress("Step 3/4", step3_done, step3_total)
            continue

        uuid3s = dedupe(bit_uuid_re.findall(text))
        names = name_re.findall(text)
        pairs = []
        if uuid3s and names:
            if len(uuid3s) == len(names):
                pairs = list(zip(uuid3s, names))
            else:
                try:
                    data = json.loads(text)
                    embedded = data.get("_embedded", {}) or data.get("embedded", {})
                    bs_list = embedded.get("bitstreams") or []
                    temp_pairs = []
                    for bs in bs_list:
                        href = ((((bs.get("_links") or {}).get("self") or {}).get("href")) or "")
                        m = bit_uuid_re.search(href)
                        u3 = m.group(1) if m else (bs.get("uuid") or "")
                        nm = bs.get("name") or ""
                        if u3 and nm:
                            temp_pairs.append((u3, nm))
                    pairs = temp_pairs if temp_pairs else [(u3, nm) for u3, nm in itertools.zip_longest(uuid3s, names, fillvalue="unknown")]
                except Exception:
                    pairs = [(u3, nm) for u3, nm in itertools.zip_longest(uuid3s, names, fillvalue="unknown")]
        elif uuid3s:
            pairs = [(u3, f"bitstream_{u3}.pdf") for u3 in uuid3s]

        # dedupe pairs
        seen_pairs, unique_pairs = set(), []
        for p in pairs:
            if p not in seen_pairs:
                seen_pairs.add(p); unique_pairs.append(p)
        bitstreams_by_bundle[bundle_uuid] = unique_pairs

        step3_done += 1
        progress("Step 3/4", step3_done, step3_total)
    print()

    # prepare download jobs
    download_jobs = []
    used_names = set()
    for bundle_uuid, pairs in bitstreams_by_bundle.items():
        for uuid3, raw_name in pairs:
            if not uuid3:
                continue
            base_name = sanitize_filename(raw_name)
            if not base_name.lower().endswith(".pdf"):
                base_name = f"{base_name}.pdf"
            final_name = base_name
            i = 2
            while final_name in used_names or os.path.exists(download_dir / final_name):
                stem, ext = os.path.splitext(base_name)
                final_name = f"{stem} ({i}){ext}"
                i += 1
            used_names.add(final_name)
            out_path = download_dir / final_name
            download_url = f"http://exampapers.ed.ac.uk/server/api/core/bitstreams/{uuid3}/content"
            download_jobs.append((download_url, str(out_path)))

    total_planned = len(download_jobs)

    # step 4: download PDFs concurrently (default 5 workers)
    step4_total = total_planned
    step4_done = 0
    downloaded_success = 0

    def _task(job):
        url, path = job
        try:
            download_with_cookie_only(url, path, COOKIE_HEADER, timeout=REQUEST_TIMEOUT)
            return True, job
        except Exception:
            return False, job

    if step4_total:
        with ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_WORKERS) as ex:
            futures = [ex.submit(_task, job) for job in download_jobs]
            for fut in as_completed(futures):
                ok, _ = fut.result()
                if ok:
                    downloaded_success += 1
                step4_done += 1
                progress("Step 4/4 (Downloading PDFs)", step4_done, step4_total)
    print()

    print("\n===== Paper Download Summary =====")
    print(f"Total papers found:               {len(item_uuids)}")
    print(f"Total available papers:           {total_planned}")
    print(f"Total available papers downloaded:{downloaded_success}")
    print(f"Total unavailable papers:         {len(item_uuids) - total_planned}")
    print("----------------------------------")
    print(f"Downloaded {downloaded_success} out of {total_planned} available paper(s).")
    print(f"Saved to: {download_dir}\n")

if __name__ == "__main__":
    main()

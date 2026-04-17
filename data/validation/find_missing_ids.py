import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import time

# --- CONFIGURATION ---
FILE_PATH = 'full_table_to_check.xlsx'
SYCO_COL = 'person_sycomore_id'
SENAT_COL = 'person_senat_id'

# Updated Headers to be more robust
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
}


def get_live_sycomore_ids():
    print("Scraping Sycomore (Assemblé Nationale)...")
    live_ids = set()
    for i in range(29, 43):
        url = f"https://www2.assemblee-nationale.fr/sycomore/liste/{i}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            # This regex captures IDs from various URL formats Sycomore uses
            ids = re.findall(r'/sycomore/fiche/\(num_dept\)/(\d+)', r.text)
            # Fallback for simpler link formats
            ids += re.findall(r'/sycomore/fiche/(\d+)', r.text)

            live_ids.update(map(int, ids))
            time.sleep(0.3)
        except Exception as e:
            print(f"  Error on Sycomore leg {i}: {e}")
    return live_ids


def get_live_senat_ids():
    print("Scraping Sénat (3ème République)...")
    url = "https://www.senat.fr/senateurs-3eme-republique/senatl.html"
    live_ids = set()
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.content, "html.parser")

        # Based on your scrape_senateurs.py, we look for links containing the path
        # or the specific 'senXXXXXX.html' format
        links = soup.find_all('a', href=True)
        for a in links:
            href = a['href']
            # Pattern 1: sen[digits].html
            match = re.search(r'sen(\d+)\.html', href)
            if match:
                live_ids.add(int(match.group(1)))
            # Pattern 2: /senateur-3eme-republique/[name][id].html
            elif "senateur-3eme-republique/" in href and href.endswith(".html"):
                # Extracts numbers from the end of the filename
                id_match = re.search(r'(\d+)\.html$', href)
                if id_match:
                    live_ids.add(int(id_match.group(1)))

        print(f"  Sénat Index: Found {len(live_ids)} IDs total.")
    except Exception as e:
        print(f"  Error on Sénat: {e}")
    return live_ids


def run_audit():
    print(f"Loading {FILE_PATH}...")
    try:
        # If your file is actually a CSV saved as .xlsx,
        # you might need pd.read_csv(FILE_PATH) instead.
        df = pd.read_excel(FILE_PATH)
    except Exception:
        df = pd.read_csv(FILE_PATH)

    # Convert to numeric and handle NaNs
    my_syco = set(pd.to_numeric(df[SYCO_COL], errors='coerce').dropna().astype(int))
    my_senat = set(pd.to_numeric(df[SENAT_COL], errors='coerce').dropna().astype(int))

    live_syco = get_live_sycomore_ids()
    live_senat = get_live_senat_ids()

    missing_syco = sorted(list(live_syco - my_syco))
    missing_senat = sorted(list(live_senat - my_senat))

    print("\n" + "=" * 50)
    print("AUDIT REPORT")
    print("=" * 50)
    print(f"SYCOMORE: {len(missing_syco)} IDs missing from Excel.")
    if missing_syco:
        print(f"IDs: {missing_syco}")

    print("-" * 30)

    print(f"SÉNAT: {len(missing_senat)} IDs missing from Excel.")
    if missing_senat:
        # Clean up the output to show the 'sen' prefix for clarity if you prefer
        print(f"IDs: {missing_senat}")
    print("=" * 50)


if __name__ == "__main__":
    run_audit()
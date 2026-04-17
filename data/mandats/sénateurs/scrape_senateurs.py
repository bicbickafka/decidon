import requests
from bs4 import BeautifulSoup
import re
import csv
import time
import os

BASE_URL = "https://www.senat.fr"
INDEX_URL = "https://www.senat.fr/senateurs-3eme-republique/senatl.html"
OUTPUT_FILE = 'senateurs.csv'


def is_in_period(date_str, start_year=1879, end_year=1945):
    if not date_str: return False
    year_match = re.search(r"\d{4}", date_str)
    if year_match:
        year = int(year_match.group(0))
        return start_year <= year <= end_year
    return False


def clean_date(date_str):
    if not date_str: return None
    return re.sub(r"\(.*?\)", "", date_str).strip()


def scrape_senator(url):
    try:
        r = requests.get(url, timeout=15)
        soup = BeautifulSoup(r.content, "html.parser")
        all_text = soup.get_text(" ", strip=True)

        h1 = soup.find("h1")
        if not h1: return []
        full_name = h1.get_text(strip=True)
        parts = full_name.split()
        prenom = parts[-1]
        nom = " ".join(parts[:-1])

        def quick_find(pat, text):
            m = re.search(pat, text, re.IGNORECASE)
            return m.group(1).strip() if m else None

        role = quick_find(r"Département\s*:\s*([\w\s\-]+?)(?=\s*(?:Ancien|Election|Elu|$))", all_text)
        birth = clean_date(quick_find(r"Né\s+le\s+([\d\w\s]+?)(?=\s*(?:à|Décédé|Elu|Profession|$))", all_text))
        death = clean_date(quick_find(r"Décédé\s+le\s+([\d\w\s]+?)(?=\s*(?:à|Elu|Fin|Profession|$))", all_text))

        # --- THE FOUGEIROL FIX ---
        # 1. Added requirement for a 4-digit year (\d{4}) in the capture
        # 2. Added Elu|Réélu to the lookahead to prevent swallowing consecutive mandates
        starts = re.findall(
            r"(?:Elu|Réélu)\s+(?:le|du)\s+([\d\w\s]+? \d{4})(?=\s*(?:au|le|Fin|Décédé|Elu|Réélu|Profession|\(|\n|$))",
            all_text, re.IGNORECASE)

        ends_range = re.findall(
            r"(?:Elu|Réélu)\s+du\s+[\d\w\s]+?\s+au\s+([\d\w\s]+?)(?=\s*(?:\(|Réélu|Elu|Fin|Décédé|$))", all_text,
            re.IGNORECASE)
        ends_standalone = re.findall(r"Fin\s+de\s+mandat\s+le\s+([\d\w\s]+?)(?=\s*(?:\(|\n|Biographies|Profession|$))",
                                     all_text, re.IGNORECASE)
        all_ends = ends_range + ends_standalone

        mandates = []
        for i in range(len(starts)):
            m_from = clean_date(starts[i])
            m_to = clean_date(all_ends[i]) if i < len(all_ends) else None

            if is_in_period(m_from) or is_in_period(m_to):
                mandates.append({
                    "nom": nom, "prenom": prenom, "role": role,
                    "from_date": m_from, "to_date": m_to,
                    "birth_date": birth, "death_date": death,
                    "senat_id": url.split("/")[-1].replace(".html", ""),
                    "url": url
                })
        return mandates
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []


# --- Main Logic with Resume Feature ---

# 1. Get existing IDs to avoid duplicates if restarting
processed_ids = set()
file_exists = os.path.isfile(OUTPUT_FILE)
if file_exists:
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            processed_ids.add(row['senat_id'])

print("Fetching index page...")
response = requests.get(INDEX_URL)
index_soup = BeautifulSoup(response.content, "html.parser")

links = []
for a in index_soup.find_all('a', href=True):
    if "senateur-3eme-republique/" in a['href'] and not a['href'].endswith("senatl.html"):
        full_link = BASE_URL + a['href'] if a['href'].startswith("/") else BASE_URL + "/" + a['href']
        links.append(full_link)

links = sorted(list(set(links)))
print(f"Found {len(links)} unique senators. Starting scrape...")

# Open in 'a' (append) mode so we don't delete existing data
with open(OUTPUT_FILE, 'a', newline='', encoding='utf-8') as f:
    fieldnames = ["nom", "prenom", "role", "from_date", "to_date", "birth_date", "death_date", "senat_id", "url"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)

    if not file_exists:
        writer.writeheader()

    for i, link in enumerate(links):
        s_id = link.split("/")[-1].replace(".html", "")
        if s_id in processed_ids:
            continue  # Skip if already in CSV

        print(f"[{i + 1}/{len(links)}] Processing: {link}")
        senator_mandates = scrape_senator(link)

        for mandate in senator_mandates:
            writer.writerow(mandate)

        f.flush()
        time.sleep(0.4)

print(f"Done! Check '{OUTPUT_FILE}'")
import requests
from bs4 import BeautifulSoup
import re
import csv
import time

BASE_URL = "https://www.senat.fr"
INDEX_URL = "https://www.senat.fr/senateurs-3eme-republique/senatl.html"


def is_in_period(date_str, start_year=1879, end_year=1945):
    """Checks if the year in a date string falls within the target range."""
    if not date_str: return False
    year_match = re.search(r"\d{4}", date_str)
    if year_match:
        year = int(year_match.group(0))
        return start_year <= year <= end_year
    return False


def clean_date(date_str):
    """Removes parenthetical noise like '( Décédé )' from dates."""
    if not date_str: return None
    return re.sub(r"\(.*?\)", "", date_str).strip()


def scrape_senator(url):
    try:
        r = requests.get(url, timeout=15)
        soup = BeautifulSoup(r.content, "html.parser")

        # 1. Flatten text with spaces to avoid merging separate HTML elements
        all_text = soup.get_text(" ", strip=True)

        # 2. Extract Identity
        h1 = soup.find("h1")
        if not h1: return []
        full_name = h1.get_text(strip=True)
        parts = full_name.split()
        prenom = parts[-1]
        nom = " ".join(parts[:-1])

        # 3. Metadata (Birth, Death, Role)
        def quick_find(pat, text):
            m = re.search(pat, text, re.IGNORECASE)
            return m.group(1).strip() if m else None

        role = quick_find(r"Département\s*:\s*([\w\s\-]+?)(?=\s*(?:Ancien|Election|Elu|$))", all_text)
        birth = clean_date(quick_find(r"Né\s+le\s+([\d\w\s]+?)(?=\s*(?:à|Décédé|Elu|Profession|$))", all_text))
        death = clean_date(quick_find(r"Décédé\s+le\s+([\d\w\s]+?)(?=\s*(?:à|Elu|Fin|Profession|$))", all_text))

        # 4. Mandate Extraction (Pairing Strategy)
        # Find all 'Starts'
        starts = re.findall(r"(?:Elu|Réélu)\s+(?:le|du)\s+([\d\w\s]+?)(?=\s*(?:au|le|Fin|Décédé|Profession|\(|\n|$))",
                            all_text, re.IGNORECASE)

        # Find all 'Ends' (both in ranges 'du...au' and standalone 'Fin de mandat le')
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

            # Apply historical period filter (1879-1945)
            if is_in_period(m_from) or is_in_period(m_to):
                mandates.append({
                    "nom": nom,
                    "prenom": prenom,
                    "role": role,
                    "from_date": m_from,
                    "to_date": m_to,
                    "birth_date": birth,
                    "death_date": death,
                    "senat_id": url.split("/")[-1].replace(".html", ""),
                    "url": url
                })
        return mandates
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []


# --- Main Logic ---

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

with open('senateurs_1879_1945.csv', 'w', newline='', encoding='utf-8') as f:
    fieldnames = ["nom", "prenom", "role", "from_date", "to_date", "birth_date", "death_date", "senat_id", "url"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for i, link in enumerate(links):
        print(f"[{i + 1}/{len(links)}] Processing: {link}")

        senator_mandates = scrape_senator(link)

        for mandate in senator_mandates:
            writer.writerow(mandate)

        # Flush to disk every record to prevent data loss
        f.flush()
        # Be polite to the server
        time.sleep(0.4)

print(f"Done! Check 'senateurs_1879_1945.csv'")
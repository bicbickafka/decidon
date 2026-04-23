import requests
from bs4 import BeautifulSoup
import re
import csv
import time

BASE_URL = "https://www2.assemblee-nationale.fr"
LIST_URLS = [
    f"https://www2.assemblee-nationale.fr/sycomore/liste/42"
]


def extract_precise(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        res = match.group(1).strip()
        # Remove common trailing artifacts
        res = re.split(r"(?:Département|à|Mandats|Profession)", res)[0].strip()
        return res
    return None


def scrape_depute_fiche(url):
    try:
        r = requests.get(url, timeout=15)
        soup = BeautifulSoup(r.content, "html.parser")

        # 1. Name
        h1 = soup.find("h1")
        if not h1: return []
        full_name = h1.get_text(strip=True)
        name_parts = full_name.split()
        nom = name_parts[-1] if name_parts else ""
        prenom = " ".join(name_parts[:-1]).strip(",") if name_parts else ""

        # 2. Birth/Death
        all_text = soup.get_text(" ", strip=True)
        birth_date = extract_precise(r"Né le ([\d\w\s]+?)(?=\s*(?:à|Décédé|Mandats))", all_text)
        death_date = extract_precise(r"Décédé le ([\d\w\s]+?)(?=\s*(?:à|Mandats))", all_text)

        # 3. Mandates
        mandates = []
        blocks = soup.find_all("dl")
        for block in blocks:
            text = block.get_text(" ", strip=True)
            if "Mandat" in text or "Régime politique" in text:
                date_range = re.search(r"Du ([\d\w\s]+) au ([\d\w\s]+)", text)
                dept_match = re.search(r"Département\s*(.*)", text)

                # Extract legislature from dt/dd pairs
                legislature = None
                dts = block.find_all("dt")
                dds = block.find_all("dd")
                for dt, dd in zip(dts, dds):
                    if "législature" in dt.get_text(strip=True).lower():
                        legislature = dd.get_text(" ", strip=True)
                        break

                if date_range:
                    to_date_clean = date_range.group(2).strip()
                    to_date_clean = re.split(r"Département", to_date_clean)[0].strip()

                    role_clean = dept_match.group(1).strip() if dept_match else None
                    if role_clean:
                        role_clean = re.split(r"(?:Législature|Mandat|Régime)", role_clean)[0].strip()

                    mandates.append({
                        "nom": nom,
                        "prenom": prenom,
                        "legislature": legislature,
                        "role": role_clean,
                        "from_date": date_range.group(1).strip(),
                        "to_date": to_date_clean,
                        "birth_date": birth_date,
                        "death_date": death_date,
                        "sycomore_id": url.split("/")[-1],
                        "url": url
                    })
        return mandates
    except Exception as e:
        print(f"Error on {url}: {e}")
        return []


# --- Main Script ---

all_deputes_links = set()

# Phase 1: Collect all links from the list page
print("Collecting links from all legislatures...")
for list_url in LIST_URLS:
    print(f"Reading list: {list_url}")
    try:
        r = requests.get(list_url)
        soup = BeautifulSoup(r.content, "html.parser")
        for a in soup.find_all('a', href=True):
            if "/sycomore/fiche/" in a['href']:
                full_link = BASE_URL + a['href']
                all_deputes_links.add(full_link)
    except Exception as e:
        print(f"Error reading list {list_url}: {e}")

print(f"Found {len(all_deputes_links)} unique deputies. Starting scrape...")

# Phase 2: Scrape each link and save to CSV
with open('deputes_chambre_16.csv', 'w', newline='', encoding='utf-8') as f:
    fieldnames = ["nom", "prenom", "legislature", "role", "from_date", "to_date", "birth_date", "death_date", "sycomore_id", "url"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for i, link in enumerate(sorted(list(all_deputes_links))):
        print(f"[{i + 1}/{len(all_deputes_links)}] Scraping: {link}")

        results = scrape_depute_fiche(link)
        for row in results:
            writer.writerow(row)

        time.sleep(0.5)

print("Scrape complete. Results saved in 'deputes_chambre_16.csv'")
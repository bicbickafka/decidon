import requests
from bs4 import BeautifulSoup
import re
import csv
import time

BASE_URL = "https://www.senat.fr"
INDEX_URL = "https://www.senat.fr/senateurs-3eme-republique/senatl.html"


def extract_precise(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        res = match.group(1).strip()
        res = re.sub(r"\(.*?\)", "", res)  # Clean parentheses
        return res.strip()
    return None


def is_in_period(date_str, start_year=1879, end_year=1945):
    """Checks if the year in a French date string is within the bounds."""
    if not date_str:
        return False
    # Look for 4 digits (the year)
    year_match = re.search(r"\d{4}", date_str)
    if year_match:
        year = int(year_match.group(0))
        return start_year <= year <= end_year
    return False


def scrape_senator(url):
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.content, "html.parser")

        h1 = soup.find("h1")
        if not h1: return None

        full_name = h1.get_text(strip=True)
        parts = full_name.split()
        prenom = parts[-1]
        nom = " ".join(parts[:-1])

        all_text = soup.get_text(" ", strip=True)

        # Patterns we refined earlier
        role_pat = r"Département\s*:\s*(.*?)(?=\s*(?:Ancien|Election|Elu|Fin))"
        from_pat = r"Elu\s+le\s+([\d\w\s]+?)(?=\s*(?:Fin|Décédé|Profession|$))"
        to_pat = r"Fin\s+de\s+mandat\s+le\s+([\d\w\s]+?)(?:\(|$)"
        birth_pat = r"Né\s+le\s+([\d\w\s]+?)(?=\s*(?:Décédé|Elu|Profession|$))"
        death_pat = r"Décédé\s+le\s+([\d\w\s]+?)(?=\s*(?:Elu|Fin|Profession|$))"

        data = {
            "nom": nom,
            "prenom": prenom,
            "role": extract_precise(role_pat, all_text),
            "from_date": extract_precise(from_pat, all_text),
            "to_date": extract_precise(to_pat, all_text),
            "birth_date": extract_precise(birth_pat, all_text),
            "death_date": extract_precise(death_pat, all_text),
            "senat_id": url.split("/")[-1].replace(".html", ""),
            "url": url
        }
        return data
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None


# --- Main Logic ---

print("Fetching index page...")
response = requests.get(INDEX_URL)
index_soup = BeautifulSoup(response.content, "html.parser")

# Find all links that look like senator profiles
# They are usually in the format: /senateur-3eme-republique/name.html
links = []
for a in index_soup.find_all('a', href=True):
    if "senateur-3eme-republique/" in a['href'] and not a['href'].endswith("senatl.html"):
        full_link = BASE_URL + a['href'] if a['href'].startswith("/") else BASE_URL + "/" + a['href']
        links.append(full_link)

# Remove duplicates
links = list(set(links))
print(f"Found {len(links)} senators. Starting filtered scrape...")

results = []

with open('senateurs_1881_1940.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=["nom", "prenom", "role", "from_date", "to_date", "birth_date", "death_date",
                                           "senat_id", "url"])
    writer.writeheader()

    for i, link in enumerate(links):
        print(f"[{i + 1}/{len(links)}] Processing: {link}")

        senator = scrape_senator(link)

        if senator:
            # Check if EITHER from_date OR to_date is between 1881 and 1940
            if is_in_period(senator['from_date']) or is_in_period(senator['to_date']):
                writer.writerow(senator)
                results.append(senator)

        # Be nice to the server
        time.sleep(0.5)

print(f"Done! Saved {len(results)} senators to senateurs_1881_1940.csv")
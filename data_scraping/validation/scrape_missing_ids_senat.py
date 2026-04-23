import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import time
import csv

# --- CONFIGURATION ---
FILE_PATH = 'full_table_to_check.xlsx'
SYCO_COL = 'person_sycomore_id'
SENAT_COL = 'person_senat_id'
OUTPUT_FILE = 'missing_records_scraped.csv'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}


# --- REUSED HELPERS FROM YOUR SCRAPE_SENATEURS.PY ---

def clean_date(date_str):
    if not date_str: return None
    return re.sub(r"\(.*?\)", "", date_str).strip()


def quick_find(pat, text):
    m = re.search(pat, text, re.IGNORECASE)
    return m.group(1).strip() if m else None


# --- SCRAPING LOGIC ---

def scrape_syco_details(id_num, url):
    """Scrapes detailed fields for Sycomore missing IDs."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.content, "html.parser")
        all_text = soup.get_text(" ", strip=True)
        results = []

        h1 = soup.find("h1")
        full_name = h1.get_text(strip=True) if h1 else ""

        # Extraction logic for birth/death similar to your deputes script
        birth = quick_find(r"Né le ([\d\w\s]+?)(?=\s*(?:à|Décédé|Mandats))", all_text)
        death = quick_find(r"Décédé le ([\d\w\s]+?)(?=\s*(?:à|Mandats))", all_text)

        for block in soup.find_all("dl"):
            text = block.get_text(" ", strip=True)
            if "législature" in text.lower():
                leg_match = re.search(r'([IVX]+e\s+législature)', text, re.IGNORECASE)
                date_range = re.search(r"Du ([\d\w\s]+) au ([\d\w\s]+)", text)

                results.append({
                    "mandature_institution": "chambre",
                    "mandature_name": leg_match.group(1) if leg_match else "",
                    "person_last_name": full_name.split()[-1] if full_name else "",
                    "person_first_name": " ".join(full_name.split()[:-1]) if full_name else "",
                    "person_birth_date": birth,
                    "person_death_date": death,
                    "mandate_start_date": date_range.group(1) if date_range else "",
                    "mandate_end_date": date_range.group(2) if date_range else "",
                    "person_sycomore_id": id_num,
                    "person_senat_id": "",
                    "url": url
                })
        return results
    except:
        return []


def scrape_senat_details(s_id, url):
    """Scrapes detailed fields for Sénat missing IDs using the 'Fougeirol Fix'."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.content, "html.parser")
        all_text = soup.get_text(" ", strip=True)

        h1 = soup.find("h1")
        full_name = h1.get_text(strip=True) if h1 else ""
        parts = full_name.split()
        prenom, nom = parts[-1], " ".join(parts[:-1])

        role = quick_find(r"Département\s*:\s*([\w\s\-]+?)(?=\s*(?:Ancien|Election|Elu|$))", all_text)
        birth = clean_date(quick_find(r"Né\s+le\s+([\d\w\s]+?)(?=\s*(?:à|Décédé|Elu|Profession|$))", all_text))
        death = clean_date(quick_find(r"Décédé\s+le\s+([\d\w\s]+?)(?=\s*(?:à|Elu|Fin|Profession|$))", all_text))

        # THE FOUGEIROL FIX INTEGRATION
        starts = re.findall(
            r"(?:Elu|Réélu)\s+(?:le|du)\s+([\d\w\s]+? \d{4})(?=\s*(?:au|le|Fin|Décédé|Elu|Réélu|Profession|\(|\n|$))",
            all_text, re.IGNORECASE)
        ends_range = re.findall(
            r"(?:Elu|Réélu)\s+du\s+[\d\w\s]+?\s+au\s+([\d\w\s]+?)(?=\s*(?:\(|Réélu|Elu|Fin|Décédé|$))",
            all_text, re.IGNORECASE)
        ends_standalone = re.findall(
            r"Fin\s+de\s+mandat\s+le\s+([\d\w\s]+?)(?=\s*(?:\(|\n|Biographies|Profession|$))",
            all_text, re.IGNORECASE)
        all_ends = ends_range + ends_standalone

        mandates = []
        for i in range(len(starts)):
            mandates.append({
                "mandature_institution": "senat",
                "mandature_name": "IIIe République",
                "person_last_name": nom,
                "person_first_name": prenom,
                "person_birth_date": birth,
                "person_death_date": death,
                "mandate_start_date": clean_date(starts[i]),
                "mandate_end_date": clean_date(all_ends[i]) if i < len(all_ends) else None,
                "person_sycomore_id": "",
                "person_senat_id": s_id,
                "url": url
            })
        return mandates
    except:
        return []


# --- AUDIT & MAIN EXECUTION ---

def get_live_sycomore_data():
    live_data = {}
    for i in range(29, 43):
        url = f"https://www2.assemblee-nationale.fr/sycomore/liste/{i}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            matches = re.findall(r'href="(/sycomore/fiche/\(num_dept\)/(\d+))"', r.text)
            for path, s_id in matches:
                live_data[int(s_id)] = "https://www2.assemblee-nationale.fr" + path
        except:
            pass
    return live_data


def get_live_senat_data():
    url = "https://www.senat.fr/senateurs-3eme-republique/senatl.html"
    live_data = {}
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.content, "html.parser")
        for a in soup.find_all('a', href=True):
            if "senateur-3eme-republique/" in a['href'] and not a['href'].endswith("senatl.html"):
                s_id = a['href'].split('/')[-1].replace('.html', '')
                live_data[s_id] = "https://www.senat.fr" + (
                    a['href'] if a['href'].startswith('/') else "/senateurs-3eme-republique/" + a['href'])
    except:
        pass
    return live_data


def run_audit():
    try:
        df = pd.read_excel(FILE_PATH)
    except:
        df = pd.read_csv(FILE_PATH)

    my_syco = set(pd.to_numeric(df[SYCO_COL], errors='coerce').dropna().astype(int))
    my_senat = set(df[SENAT_COL].dropna().astype(str))

    live_syco_map = get_live_sycomore_data()
    live_senat_map = get_live_senat_data()

    missing_syco_ids = [sid for sid in live_syco_map if sid not in my_syco]
    missing_senat_ids = [sid for sid in live_senat_map if sid not in my_senat]

    final_rows = []

    print(f"Scraping {len(missing_syco_ids)} missing Sycomore records...")
    for sid in missing_syco_ids:
        final_rows.extend(scrape_syco_details(sid, live_syco_map[sid]))
        time.sleep(0.2)

    print(f"Scraping {len(missing_senat_ids)} missing Sénat records...")
    for sid in missing_senat_ids:
        final_rows.extend(scrape_senat_details(sid, live_senat_map[sid]))
        time.sleep(0.2)

    if final_rows:
        pd.DataFrame(final_rows).to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig', sep=';')
        print(f"Audit Complete. {len(final_rows)} mandate records saved to {OUTPUT_FILE}")
    else:
        print("Audit Complete. No missing records found.")


if __name__ == "__main__":
    run_audit()
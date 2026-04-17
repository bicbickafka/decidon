import requests
from bs4 import BeautifulSoup
import re

url = "https://www2.assemblee-nationale.fr/sycomore/fiche/25"

r = requests.get(url)
soup = BeautifulSoup(r.content, "html.parser")

# --- 1. Identity ---
# The name is usually in the breadcrumb or the main title
title_tag = soup.find("h1")
full_name = title_tag.get_text(strip=True) if title_tag else ""
name_parts = full_name.split()
nom = name_parts[-1] if name_parts else ""
prenom = " ".join(name_parts[:-1]).strip(",") if name_parts else ""

# Get all text to extract Birth/Death
all_text = soup.get_text(" ", strip=True)


def extract_date(pattern, text):
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


birth_date = extract_date(r"Né le ([\d\w\s]+?)(?=\s*(?:à|Décédé|Mandats))", all_text)
death_date = extract_date(r"Décédé le ([\d\w\s]+?)(?=\s*(?:à|Mandats))", all_text)

# --- 2. Mandate Extraction (The tricky part) ---
mandates_data = []

# Sycomore groups mandates inside 'article' or specific 'div' blocks
# We'll look for blocks that contain the string "Régime politique"
mandate_blocks = soup.find_all("div", class_="info-mandat")
# If 'info-mandat' class doesn't exist, we fallback to finding the headers
if not mandate_blocks:
    mandate_blocks = soup.find_all("dl")  # Many Sycomore pages use <dl> lists

for block in mandate_blocks:
    block_text = block.get_text(" ", strip=True)

    # We only care about blocks that actually describe a mandate
    if "Régime politique" in block_text or "Mandat" in block_text:

        # Extract Dates: "Du 23 mars 1884 au 14 octobre 1885"
        date_range = re.search(r"Du ([\d\w\s]+) au ([\d\w\s]+)", block_text)

        # Extract Department: Usually follows the word "Département"
        dept_match = re.search(r"Département\s*([\w\s\-]+)", block_text)

        if date_range:
            mandates_data.append({
                "nom": nom,
                "prenom": prenom,
                "role": dept_match.group(1).strip() if dept_match else None,
                "from_date": date_range.group(1).strip(),
                "to_date": date_range.group(2).strip(),
                "birth_date": birth_date,
                "death_date": death_date,
                "sycomore_id": url.split("/")[-1],
                "url": url
            })

# --- Final Check ---
if not mandates_data:
    print("DEBUG: No mandates found. Checking raw text...")
    # This will help us see what the script is actually seeing
    if "Mandat" in all_text:
        print("DEBUG: 'Mandat' text is present but regex/tags failed.")
else:
    for m in mandates_data:
        print(m)
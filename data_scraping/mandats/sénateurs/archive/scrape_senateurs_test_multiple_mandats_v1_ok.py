import requests
from bs4 import BeautifulSoup
import re

url = "https://www.senat.fr/senateur-3eme-republique/foucher_de_careil_louis1576r3.html"

r = requests.get(url)
soup = BeautifulSoup(r.content, "html.parser")

# --- 1. Basic Identity (Fixed for all mandates) ---
h1 = soup.find("h1").get_text(strip=True)
parts = h1.split()
prenom = parts[-1]
nom = " ".join(parts[:-1])
senat_id = url.split("/")[-1].replace(".html", "")

all_text = soup.get_text(" ", strip=True)


def extract_precise(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        res = match.group(1).strip()
        res = re.sub(r"\(.*?\)", "", res)
        return res.strip()
    return None


birth_date = extract_precise(r"Né\s+le\s+([\d\w\s]+?)(?=\s*(?:Décédé|Elu|Profession|$))", all_text)
death_date = extract_precise(r"Décédé\s+le\s+([\d\w\s]+?)(?=\s*(?:Elu|Fin|Profession|$))", all_text)
role = extract_precise(r"Département\s*:\s*(.*?)(?=\s*(?:Ancien|Election|Elu|Fin))", all_text)

# --- 2. Mandate Extraction (Revised) ---
mandates = []

# 1. Catch all "du [date] au [date]" patterns
# This handles: "Elu du 30 janvier 1876 au 7 janvier 1882"
# and "Réélu du 8 janvier 1882 au 3 janvier 1891"
ranges = re.findall(r"(?:Elu|Réélu)\s+du\s+([\d\w\s]+?)\s+au\s+([\d\w\s]+?)(?=\s*(?:\(|Réélu|Elu|Fin|Décédé|$))", all_text, re.IGNORECASE)

for start, end in ranges:
    mandates.append({
        "from": start.strip(),
        "to": end.strip()
    })

# 2. Catch the "le [date] ... Fin de mandat le [date]" pattern
# This handles the final: "Réélu le 4 janvier 1891 ... Fin de mandat le 10 janvier 1891"
event_froms = re.findall(r"(?:Elu|Réélu)\s+le\s+([\d\w\s]+?)(?=\s*(?:Réélu|Elu|Fin|Décédé|$))", all_text, re.IGNORECASE)
event_tos = re.findall(r"Fin\s+de\s+mandat\s+le\s+([\d\w\s]+?)(?:\(|$)", all_text, re.IGNORECASE)

# Logic: If we have an "Elu le" that wasn't already caught in the "du/au" ranges,
# pair it with the corresponding "Fin de mandat le"
for f_date in event_froms:
    # Check if this start date is already in our mandates list
    if not any(m['from'] == f_date.strip() for m in mandates):
        # Find the to_date that appears AFTER this from_date in the text (usually the last one)
        # For simplicity, since "Fin de mandat le" is almost always the last one on the page:
        corresp_to = event_tos[-1] if event_tos else None
        mandates.append({
            "from": f_date.strip(),
            "to": corresp_to.strip() if corresp_to else None
        })

# --- 3. Final Formatting ---
results = []
for m in mandates:
    results.append({
        "nom": nom,
        "prenom": prenom,
        "role": role,
        "from_date": m["from"],
        "to_date": m["to"],
        "birth_date": birth_date,
        "death_date": death_date,
        "senat_id": senat_id,
        "url": url
    })

for r in results:
    print(r)
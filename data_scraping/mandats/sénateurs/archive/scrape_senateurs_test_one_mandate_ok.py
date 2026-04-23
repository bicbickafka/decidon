import requests
from bs4 import BeautifulSoup
import re

url = "https://www.senat.fr/senateur-3eme-republique/abeille_valentin0093r3.html"

r = requests.get(url)
soup = BeautifulSoup(r.content, "html.parser")

# --- Name ---
h1 = soup.find("h1").get_text(strip=True)
parts = h1.split()
prenom = parts[-1]
nom = " ".join(parts[:-1])

# --- Content Extraction ---
all_text = soup.get_text(" ", strip=True)

def extract_precise(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        res = match.group(1).strip()
        # Clean up parentheses and common trailing artifacts
        res = re.sub(r"\(.*?\)", "", res)
        return res.strip()
    return None

# --- Improved Patterns with explicit stop-words ---
# Stops before "Ancien", "Election", or "Elu"
role_pattern = r"Département\s*:\s*(.*?)(?=\s*(?:Ancien|Election|Elu|Fin))"

# Stops before "Décédé", "Elu", or "Profession"
birth_pattern = r"Né\s+le\s+([\d\w\s]+?)(?=\s*(?:Décédé|Elu|Profession|$))"

# Stops before "Elu", "Fin", or "Profession"
death_pattern = r"Décédé\s+le\s+([\d\w\s]+?)(?=\s*(?:Elu|Fin|Profession|$))"

senator_data = {
    "nom": nom,
    "prenom": prenom,
    "role": extract_precise(role_pattern, all_text),
    "from_date": extract_precise(r"Elu\s+le\s+([\d\w\s]+?)(?=\s*(?:Fin|Décédé|Profession|$))", all_text),
    "to_date": extract_precise(r"Fin\s+de\s+mandat\s+le\s+([\d\w\s]+?)(?:\(|$)", all_text),
    "birth_date": extract_precise(birth_pattern, all_text),
    "death_date": extract_precise(death_pattern, all_text),
    "senat_id": url.split("/")[-1].replace(".html", ""),
    "url": url
}

print(senator_data)
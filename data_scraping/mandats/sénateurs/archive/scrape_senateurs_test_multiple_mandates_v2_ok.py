import requests
from bs4 import BeautifulSoup
import re

url = "https://www.senat.fr/senateur-3eme-republique/fougeirol_edouard0132r3.html"
r = requests.get(url)
soup = BeautifulSoup(r.content, "html.parser")
all_text = soup.get_text(" ", strip=True)

# 1. Identity
h1 = soup.find("h1").get_text(strip=True)
parts = h1.split()
prenom = parts[-1]
nom = " ".join(parts[:-1])

# 2. THE FIX: Refined Starts and Ends
# We added a requirement that the start date must have a month/year nearby
# and shouldn't just be a single stray digit.
starts = re.findall(r"(?:Elu|Réélu)\s+(?:le|du)\s+([\d\w\s]+? \d{4})(?=\s*(?:au|le|Fin|Décédé|Elu|Réélu|Profession|\(|\n|$))", all_text, re.IGNORECASE)

# Find all possible end markers
ends_range = re.findall(r"(?:Elu|Réélu)\s+du\s+[\d\w\s]+?\s+au\s+([\d\w\s]+?)(?=\s*(?:\(|Réélu|Elu|Fin|Décédé|$))", all_text, re.IGNORECASE)
ends_standalone = re.findall(r"Fin\s+de\s+mandat\s+le\s+([\d\w\s]+?)(?=\s*(?:\(|\n|Biographies|Profession|$))", all_text, re.IGNORECASE)
all_ends = ends_range + ends_standalone

# 3. Pairing Logic
results = []
for i in range(len(starts)):
    m_from = starts[i].strip()
    # We pair the Nth start with the Nth end.
    # For Fougeirol, the 'Fin de mandat' (1912) technically applies
    # to the last mandate he held.
    m_to = all_ends[i].strip() if i < len(all_ends) else None

    results.append({
        "nom": nom,
        "prenom": prenom,
        "from_date": m_from,
        "to_date": m_to
    })

for res in results:
    print(res)
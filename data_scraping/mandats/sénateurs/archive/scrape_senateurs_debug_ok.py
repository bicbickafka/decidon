import requests
from bs4 import BeautifulSoup
import re

url = "https://www.senat.fr/senateur-3eme-republique/depierre_joseph1152r3.html"
r = requests.get(url)
soup = BeautifulSoup(r.content, "html.parser")

# 1. Flatten the text with a clear space separator
# This ensures that "1936" and "Fin" don't touch each other
all_text = soup.get_text(" ", strip=True)

# 2. Extract Identity
h1 = soup.find("h1").get_text(strip=True)
parts = h1.split()
prenom = parts[-1]
nom = " ".join(parts[:-1])

# 3. Find ALL "Start" dates (Elu le/du)
# Result for Depierre: ['14 janvier 1936']
starts = re.findall(r"(?:Elu|Réélu)\s+(?:le|du)\s+([\d\w\s]+?)(?=\s*(?:au|Fin|Décédé|Profession|\(|\n|$))", all_text,
                    re.IGNORECASE)

# 4. Find ALL "End" dates (Fin de mandat le / au ...)
# Result for Depierre: ['31 décembre 1944']
ends = re.findall(r"(?:Fin\s+de\s+mandat\s+le|au)\s+([\d\w\s]+?)(?=\s*(?:\(|\n|Biographies|Profession|$))", all_text,
                  re.IGNORECASE)


# 5. Metadata (Birth, Death, Role)
def quick_find(pat, text):
    m = re.search(pat, text, re.IGNORECASE)
    return m.group(1).strip() if m else None


# Clean up Role to stop before "Ancien"
role = quick_find(r"Département\s*:\s*([\w\s\-]+?)(?=\s*(?:Ancien|Election|$))", all_text)
birth = quick_find(r"Né\s+le\s+([\d\w\s]+?)(?=\s*(?:à|Décédé|Elu|$))", all_text)
death = quick_find(r"Décédé\s+le\s+([\d\w\s]+?)(?=\s*(?:à|Elu|Fin|$))", all_text)

# 6. Pair them up
results = []
for i in range(len(starts)):
    # We match start[i] with end[i]
    m_to = ends[i].strip() if i < len(ends) else None

    results.append({
        "nom": nom,
        "prenom": prenom,
        "role": role,
        "from_date": starts[i].strip(),
        "to_date": m_to,
        "birth_date": birth,
        "death_date": death,
        "senat_id": url.split("/")[-1].replace(".html", ""),
        "url": url
    })

for res in results:
    print(res)
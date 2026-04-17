"""
Fetch birth and death dates from senat.fr pages for IIIe République members.
Run: pip install requests beautifulsoup4 pandas
     python fetch_senat_dates.py
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

# Map wikidata_qid -> senat_id (from your document + known mappings)
# You can extend this dict or feed it from your Excel file directly
QID_TO_SENAT_ID = {
    "Q18384890": "berard_leon0082r3",
    "Q475755":   "dumont_charles0258r3",
    "Q2947187":  "morel_jean0400r3",
    "Q20660467": "lafont_ernest0329r3",
    "Q3262636":  "marin_louis0277r3",
    "Q16060769": "maurin_louis0339r3",
    "Q21294910": "cavaignac_godefroy0075r3",
    "Q3171014":  "brun_jean0063r3",
    "Q3171879":  "dupuy_jean0264r3",
    "Q125250":   "durand_jean0270r3",
    "Q2406228":  "raynaud_maurice0470r3",
    "Q363255":   "thomas_albert0536r3",
    "Q3265579":  "lamoureux_lucien0337r3",
    "Q293001":   "carnot_sadi0076r3",
    "Q3056857":  "boulanger_ernest0054r3",
    "Q3102323":  "bonnet_georges0046r3",
    "Q5080038":  "lambert_charles0331r3",
    "Q2958866":  "delesalle_charles0166r3",
    "Q3261710":  "deschamps_louis0174r3",
    "Q3261764":  "dubois_louis0221r3",
    "Q5728332":  "simon_henry0520r3",
    "Q3261042":  "andre_louis0010r3",
    "Q3370621":  "bernier_paul0039r3",
    "Q3289369":  "regnier_marcel0472r3",
    "Q3103417":  "rivollet_georges0484r3",
    "Q3385902":  "legrand_pierre0344r3",
    "Q61068649": "terrier_louis0534r3",
    "Q3557423":  "lourties_victor0378r3",
    "Q3386819":  "robert_pierre0483r3",
    "Q21074190": "lebon_andre0341r3",
    "Q20661173": "renard_andre0473r3",
    "Q16032275": "isaac_auguste0311r3",
    "Q935896":   "stern_jacques0527r3",
    "Q18384898": "besse_rene0040r3",
    "Q1635623":  "bernard_jean0037r3",
    "Q3265545":  "hubert_lucien0308r3",
    "Q2831367":  "mahieu_albert0385r3",
    "Q126307762":"brunet_auguste0066r3",
}

BASE_URL = "https://www.senat.fr/senateur-3eme-republique/{slug}.html"

def parse_date(text):
    """Extract a date string like '12 mars 1870' from text."""
    months = {
        "janvier":"01","février":"02","mars":"03","avril":"04",
        "mai":"05","juin":"06","juillet":"07","août":"08",
        "septembre":"09","octobre":"10","novembre":"11","décembre":"12"
    }
    m = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})', text)
    if m:
        day, month, year = m.group(1), m.group(2).lower(), m.group(3)
        return f"{year}-{months.get(month,'??')}-{int(day):02d}"
    # year only
    m = re.search(r'\b(1[89]\d{2})\b', text)
    if m:
        return m.group(1)
    return ""

rows = []
for qid, slug in QID_TO_SENAT_ID.items():
    url = BASE_URL.format(slug=slug)
    try:
        r = requests.get(url, headers={"User-Agent": "research-bot/1.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        birth, death = "", ""
        # Look for "Né le" / "Décédé le" in the état civil section
        text = soup.get_text(" ", strip=True)
        born = re.search(r'Né\s+le\s+([\d\w\s]+?\d{4})', text)
        died = re.search(r'Décédé\s+le\s+([\d\w\s]+?\d{4})', text)
        if born:
            birth = parse_date(born.group(1))
        if died:
            death = parse_date(died.group(1))

        print(f"{qid} {slug}: {birth} → {death}")
        rows.append({"wikidata_qid": qid, "senat_id": slug, "birth_date": birth, "death_date": death})
    except Exception as e:
        print(f"ERROR {qid} {slug}: {e}")
        rows.append({"wikidata_qid": qid, "senat_id": slug, "birth_date": "", "death_date": ""})
    time.sleep(0.3)  # be polite

df = pd.DataFrame(rows)
df.to_csv("senat_dates.csv", index=False)
print("\nDone. Saved to senat_dates.csv")
print(df.to_string())

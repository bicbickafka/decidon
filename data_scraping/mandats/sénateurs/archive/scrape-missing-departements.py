import requests
from bs4 import BeautifulSoup
import re
import csv

# Your unique list of IDs
raw_ids = [
    "lucet_jacques0690r3", "lelievre_ferdinand0836r3", "lacomme_claude0530r3",
    "joigneaux_pierre0546r3", "spuller_eugene0548r3", "pomel_nicolas1821r3",
    "aubry_charles0694r3", "mazeau_charles0538r3", "jacques_remy1822r3",
    "hugot_louis0531r3", "piot_edme0550r3", "lesueur_georges0692r3",
    "ricard_henri0543r3", "desbassyns_de_richemont_pierre1828r3", "gerente_paul0838r3",
    "messner_ernest0552r3", "mauguin_alexandre0837r3", "forcioli_dominique0691r3",
    "colin_maurice0839r3", "flandin_etienne1832r3", "etienne_eugene1824r3",
    "treille_alcide0693r3", "philipot_anatole0532r3", "godin_jules1831r3",
    "bluysen_paul1835r3", "saurin_paul1826r3", "montenot_auguste0533r3",
    "gaebele_henri1834r3", "saint_germain_marcel1823r3", "chauveau_claude0544r3",
    "jossot_pierre0554r3", "duroux_jacques0840r3", "le_moignic_eugene1836r3",
    "vincent_emile0534r3", "cuttoli_paul0695r3", "roux_freissineng_pierre1827r3",
    "mallarme_andre0841r3", "gasser_jules0350r4"
]

# Use set() to remove duplicates automatically
unique_ids = sorted(list(set(raw_ids)))
output_file = 'senateurs_data.csv'


def get_match(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def scrape_senator(s_id):
    url = f"https://www.senat.fr/senateur-3eme-republique/{s_id}.html"
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.content, "html.parser")
        all_text = soup.get_text(" ", strip=True)
        h1 = soup.find("h1")

        return {
            "nom": h1.get_text(strip=True) if h1 else "Unknown",
            "departement": get_match(
                r"Département\s*:\s*(.*?)(?=\s*(?:Ancien|Election|Elu|Fin|Profession|Né|Décédé|$))", all_text),
            "birth": get_match(r"Né\s+le\s+([\d\w\s]+?)(?=\s*(?:Décédé|Elu|Profession|$))", all_text),
            "death": get_match(r"Décédé\s+le\s+([\d\w\s]+?)(?=\s*(?:Elu|Fin|Profession|$))", all_text),
            "senat_id": s_id
        }
    except Exception as e:
        print(f"Error scraping {s_id}: {e}")
        return None


# Execution
with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=["nom", "departement", "birth", "death", "senat_id"])
    writer.writeheader()

    for s_id in unique_ids:
        print(f"Scraping {s_id}...")
        data = scrape_senator(s_id)
        if data:
            writer.writerow(data)

print(f"Done! Data saved to {output_file}")
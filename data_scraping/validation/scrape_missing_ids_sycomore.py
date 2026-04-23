import requests
from bs4 import BeautifulSoup
import re
import csv
import time

# --- CONFIGURATION ---
SYCO_IDS = [16, 158, 160, 162, 167, 168, 494, 1581, 1582, 1589, 1591, 1596, 1597, 1598, 1599, 1600, 1601, 1603, 1604,
            1606, 1607, 1609, 1616, 1617, 1618, 1633, 1641, 1649, 1664, 1666, 1669, 1673, 1683, 1685, 1703, 16160]
SENAT_IDS = [3, 4, 672, 685, 746]
OUTPUT_FILE = 'missing_records_final.csv'


# --- LOGIQUE RÉUTILISÉE DE VOS SCRIPTS ---

def extract_precise(pattern, text):
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        res = match.group(1).strip()
        res = re.split(r"(?:Département|à|Mandats|Profession)", res)[0].strip()
        return res
    return None


def clean_date(date_str):
    if not date_str: return None
    return re.sub(r"\(.*?\)", "", date_str).strip()


def scrape_depute_fiche(id_num):
    url = f"https://www2.assemblee-nationale.fr/sycomore/fiche/(num_dept)/{id_num}"
    try:
        r = requests.get(url, timeout=15)
        soup = BeautifulSoup(r.content, "html.parser")
        h1 = soup.find("h1")
        if not h1: return []

        full_name = h1.get_text(strip=True)
        name_parts = full_name.split()
        nom = name_parts[-1] if name_parts else ""
        prenom = " ".join(name_parts[:-1]).strip(",") if name_parts else ""

        all_text = soup.get_text(" ", strip=True)
        birth = extract_precise(r"Né le ([\d\w\s]+?)(?=\s*(?:à|Décédé|Mandats))", all_text)
        death = extract_precise(r"Décédé le ([\d\w\s]+?)(?=\s*(?:à|Mandats))", all_text)

        mandates = []
        # Sycomore utilise des balises <dl> pour les mandats
        for block in soup.find_all("dl"):
            text = block.get_text(" ", strip=True)
            if "Mandat" in text or "Régime politique" in text:
                date_range = re.search(r"Du ([\d\w\s]+) au ([\d\w\s]+)", text)
                dept_match = re.search(r"Département\s*(.*)", text)

                # EXTRACTION DE LA LÉGISLATURE (ex: VIe législature)
                leg_match = re.search(r"([IVX]+e législature)", text, re.IGNORECASE)

                if date_range:
                    to_date = re.split(r"Département", date_range.group(2).strip())[0].strip()
                    role = dept_match.group(1).strip() if dept_match else ""
                    role = re.split(r"(?:Législature|Mandat|Régime)", role)[0].strip()

                    # On place la législature dans mandature_name pour correspondre à votre table
                    legislature = leg_match.group(1).strip() if leg_match else ""

                    mandates.append({
                        "mandature_institution": "chambre",
                        "mandature_name": legislature,
                        "person_last_name": nom,
                        "person_first_name": prenom,
                        "mandate_position": role,
                        "mandate_start_date": date_range.group(1).strip(),
                        "mandate_end_date": to_date,
                        "person_birth_date": birth,
                        "person_death_date": death,
                        "person_sycomore_id": id_num,
                        "url": url
                    })
        return mandates
    except Exception as e:
        print(f"Erreur Sycomore {id_num}: {e}")
        return []


def scrape_senator(id_num):
    url = f"https://www.senat.fr/senateur-3eme-republique/sen{str(id_num).zfill(6)}.html"
    try:
        r = requests.get(url, timeout=15)
        soup = BeautifulSoup(r.content, "html.parser")
        all_text = soup.get_text(" ", strip=True)
        h1 = soup.find("h1")
        if not h1: return []
        full_name = h1.get_text(strip=True)
        parts = full_name.split()
        prenom, nom = parts[-1], " ".join(parts[:-1])

        role = extract_precise(r"Département\s*:\s*([\w\s\-]+?)(?=\s*(?:Ancien|Election|Elu|$))", all_text)
        birth = clean_date(extract_precise(r"Né\s+le\s+([\d\w\s]+?)(?=\s*(?:à|Décédé|Elu|Profession|$))", all_text))
        death = clean_date(extract_precise(r"Décédé\s+le\s+([\d\w\s]+?)(?=\s*(?:à|Elu|Fin|Profession|$))", all_text))

        # Utilisation de votre correctif "FOUGEIROL"
        starts = re.findall(r"(?:Elu|Réélu)\s+(?:le|du)\s+([\d\w\s]+? \d{4})", all_text, re.IGNORECASE)
        ends_range = re.findall(r"au\s+([\d\w\s]+?)(?=\s*(?:\(|Réélu|Elu|Fin|Décédé|$))", all_text, re.IGNORECASE)
        ends_standalone = re.findall(r"Fin\s+de\s+mandat\s+le\s+([\d\w\s]+?)", all_text, re.IGNORECASE)
        all_ends = ends_range + ends_standalone

        mandates = []
        for i in range(len(starts)):
            mandates.append({
                "mandature_institution": "senat",
                "mandature_name": "IIIe République",
                "person_last_name": nom,
                "person_first_name": prenom,
                "mandate_position": role,
                "mandate_start_date": clean_date(starts[i]),
                "mandate_end_date": clean_date(all_ends[i]) if i < len(all_ends) else None,
                "person_birth_date": birth,
                "person_death_date": death,
                "person_senat_id": id_num,
                "url": url
            })
        return mandates
    except Exception as e:
        print(f"Erreur Senat {id_num}: {e}")
        return []


# --- EXÉCUTION ---

fieldnames = [
    "mandature_institution", "mandature_name", "person_last_name", "person_first_name",
    "person_birth_date", "person_death_date", "person_sycomore_id", "person_senat_id",
    "mandate_position", "mandate_start_date", "mandate_end_date", "url"
]

with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    print(f"Récupération de {len(SYCO_IDS)} IDs Sycomore...")
    for sid in SYCO_IDS:
        for row in scrape_depute_fiche(sid):
            # On s'assure que person_senat_id est vide pour la Chambre
            row["person_senat_id"] = ""
            writer.writerow(row)
        time.sleep(0.3)

    print(f"Récupération de {len(SENAT_IDS)} IDs Sénat...")
    for sid in SENAT_IDS:
        for row in scrape_senator(sid):
            # On s'assure que person_sycomore_id est vide pour le Sénat
            row["person_sycomore_id"] = ""
            writer.writerow(row)
        time.sleep(0.3)

print(f"Terminé ! Résultats enregistrés dans {OUTPUT_FILE}")
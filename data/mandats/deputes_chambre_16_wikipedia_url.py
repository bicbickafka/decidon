import pandas as pd
import requests
import time
import os

def fetch_exact_wikipedia(qid):
    """
    Queries Wikidata for the French Wikipedia URL associated with a QID.
    """
    if pd.isna(qid) or not str(qid).startswith('Q'):
        return ""

    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "format": "json",
        "props": "sitelinks",
        "sitefilter": "frwiki"
    }

    headers = {
        'User-Agent': 'MargueriteDataProject/1.0 (contact: mfresq@example.com)'
    }

    for attempt in range(3):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                entities = data.get("entities", {})
                if qid in entities:
                    sitelinks = entities[qid].get("sitelinks", {})
                    if "frwiki" in sitelinks:
                        exact_title = sitelinks["frwiki"]["title"]
                        # We use .replace to ensure a valid URL format
                        return f"https://fr.wikipedia.org/wiki/{exact_title.replace(' ', '_')}"
                return ""

            elif response.status_code == 429:
                print(f"  Surcharge (429) pour {qid}, pause de 10s...")
                time.sleep(10)
            else:
                time.sleep(2)

        except Exception:
            if attempt < 2:
                time.sleep(3)
                continue
    return ""

# --- CONFIGURATION (Matching your file names) ---
input_file = 'chambre_16_wiki_qid_completed.xlsx'
output_file = 'chambre_16_full_enriched.xlsx'

if not os.path.exists(input_file):
    print(f"Erreur : Le fichier '{input_file}' est introuvable.")
else:
    print(f"Chargement de {input_file}...")
    df = pd.read_excel(input_file)

    # Ensure the URL column is treated as text to avoid warnings
    df['person_wikipedia_url_no_hyperlink'] = df['person_wikipedia_url_no_hyperlink'].astype(object)

    # 1. Extraction of unique QIDs to minimize API calls
    unique_qids = df['person_wikidata_qid'].dropna().unique()
    mapping_wikipedia = {}
    total = len(unique_qids)

    print(f"Début de la récupération pour {total} individus uniques...")

    for i, qid in enumerate(unique_qids):
        if (i + 1) % 50 == 0 or (i + 1) == total:
            print(f"Progression : {i + 1}/{total} ({(i + 1) / total * 100:.1f}%)")

        mapping_wikipedia[qid] = fetch_exact_wikipedia(qid)

        # Respectful delay for Wikimedia API
        time.sleep(0.2)

    # 2. Update the specific column in your sheet
    print("Mise à jour de la colonne Wikipedia...")
    df['person_wikipedia_url_no_hyperlink'] = df['person_wikidata_qid'].map(mapping_wikipedia)

    # 3. Final Save to Excel
    df.to_excel(output_file, index=False)

    print("-" * 30)
    print(f"SUCCÈS ! Fichier enrichi créé : {output_file}")
    print(f"Nombre total de lignes : {len(df)}")
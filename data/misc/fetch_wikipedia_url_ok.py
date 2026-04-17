import pandas as pd
import requests
import time
import os


def fetch_exact_wikipedia(qid):
    """
    Interroge Wikidata avec un système de sécurité (Retry) 
    pour éviter les erreurs 'line 1 column 1'.
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

    # User-Agent recommandé par la fondation Wikimedia
    headers = {
        'User-Agent': 'MargueriteDataProject/1.0 (contact: mfresq@example.com)'
    }

    # Tentatives (max 3 essais par QID)
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
                        return f"https://fr.wikipedia.org/wiki/{exact_title.replace(' ', '_')}"
                return ""  # Pas de page wiki trouvée

            elif response.status_code == 429:  # Trop de requêtes
                print(f"Surcharge (429) pour {qid}, pause de 10s...")
                time.sleep(10)
            else:
                time.sleep(2)  # Autre erreur serveur, on attend un peu

        except Exception:
            if attempt < 2:
                time.sleep(3)  # Pause avant le prochain essai
                continue

    return ""


# --- CONFIGURATION ---
input_file = 'full_table.xlsx'
output_file = 'full_table_with_wikipedia.csv'

if not os.path.exists(input_file):
    print(f"Erreur : Le fichier '{input_file}' est introuvable.")
else:
    # 1. Chargement (Gestion Excel)
    print(f"Chargement de {input_file}...")
    try:
        df = pd.read_excel(input_file)
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier Excel : {e}")
        exit()

    # 2. Extraction des QID uniques
    unique_qids = df['person_wikidata_qid'].dropna().unique()
    mapping_wikipedia = {}
    total = len(unique_qids)

    print(f"Début de la récupération pour {total} individus uniques...")
    print("Cette opération va prendre environ 20-30 minutes. Ne fermez pas le terminal.")

    for i, qid in enumerate(unique_qids):
        # Log de progression toutes les 50 lignes
        if (i + 1) % 50 == 0 or (i + 1) == total:
            print(f"Progression : {i + 1}/{total} ({(i + 1) / total * 100:.1f}%)")

        # Appel API avec sécurité
        mapping_wikipedia[qid] = fetch_exact_wikipedia(qid)

        # Pause de sécurité (0.2s = ~5 requêtes par seconde, ce que Wikidata accepte)
        time.sleep(0.2)

    # 3. Mise à jour de la table originale
    print("Mise à jour des colonnes...")
    df['wikipedia_url'] = df['person_wikidata_qid'].map(mapping_wikipedia)

    # 4. Sauvegarde finale en CSV
    # encoding='utf-8-sig' permet à Excel d'ouvrir le fichier avec les bons accents
    df.to_csv(output_file, index=False, encoding='utf-8-sig')

    print("-" * 30)
    print(f"SUCCÈS ! Fichier enrichi créé : {output_file}")
    print(f"Nombre total de lignes traitées : {len(df)}")
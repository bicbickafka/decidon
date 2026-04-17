import pandas as pd
import requests
import time
import os
from tqdm import tqdm


def get_dates_from_wikidata(qid):
    """
    Récupère les dates de naissance (P569) et de décès (P570) depuis Wikidata.
    """
    if pd.isna(qid) or not str(qid).startswith('Q'):
        return None, None

    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "format": "json",
        "props": "claims"
    }

    headers = {'User-Agent': 'BotMarguerite/1.0 (Contact: via_python_requests)'}

    try:
        res = requests.get(url, params=params, headers=headers, timeout=10).json()
        entity = res.get('entities', {}).get(qid, {})
        claims = entity.get('claims', {})

        def extract_date(prop_id):
            prop_claims = claims.get(prop_id, [])
            if not prop_claims:
                return None
            try:
                date_str = prop_claims[0]['mainsnak']['datavalue']['value']['time']
                # Nettoyage : +1866-10-16T00:00:00Z -> 1866-10-16
                # On gère aussi les dates anciennes qui commencent par '-'
                if date_str.startswith('+'):
                    return date_str.lstrip('+').split('T')[0]
                return date_str.split('T')[0]
            except (KeyError, IndexError, TypeError):
                return None

        birth = extract_date('P569')
        death = extract_date('P570')
        return birth, death
    except Exception as e:
        print(f"Erreur API pour {qid}: {e}")
        return None, None


# --- CONFIGURATION ---
# Vérifiez bien que le nom du fichier ci-dessous est exact dans votre dossier
input_file = 'scrape_death_dates.xlsx'
output_file = 'table_avec_dates_maj.csv'

# --- CHARGEMENT DES DONNÉES AVEC GESTION D'ERREURS ---
print(f"Chargement de {input_file}...")

if not os.path.exists(input_file):
    print(f"Erreur : Le fichier '{input_file}' est introuvable dans le dossier.")
    exit()

try:
    if input_file.endswith('.xlsx'):
        df = pd.read_excel(input_file)
    else:
        # Tentative de lecture CSV avec gestion de l'encodage (Latin-1 pour Excel)
        try:
            df = pd.read_csv(input_file, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(input_file, encoding='latin-1')
except Exception as e:
    print(f"Erreur lors de la lecture du fichier : {e}")
    exit()

# --- TRAITEMENT ---
# On identifie les QID uniques
unique_qids = df['wikidata_qid'].dropna().unique()
results_cache = {}

print(f"Récupération des dates pour {len(unique_qids)} individus sur Wikidata...")

for qid in tqdm(unique_qids):
    birth, death = get_dates_from_wikidata(qid)
    results_cache[qid] = {
        'birth_date_wd': birth,
        'death_date_wd': death
    }
    time.sleep(0.2)  # Respect de l'API

print("\nApplication des données au tableau...")
res_df = pd.DataFrame.from_dict(results_cache, orient='index').reset_index()
res_df.columns = ['wikidata_qid', 'birth_date_wd', 'death_date_wd']

df = df.merge(res_df, on='wikidata_qid', how='left')

# Mise à jour des colonnes (on ne remplit que si c'est vide)
if 'birth_date' in df.columns:
    df['birth_date'] = df['birth_date'].fillna(df['birth_date_wd'])
else:
    df['birth_date'] = df['birth_date_wd']

if 'death_date' in df.columns:
    df['death_date'] = df['death_date'].fillna(df['death_date_wd'])
else:
    df['death_date'] = df['death_date_wd']

# Nettoyage
df = df.drop(columns=['birth_date_wd', 'death_date_wd'])

# Sauvegarde finale en UTF-8-SIG (format universel pour Excel et Python)
df.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"Terminé ! Fichier enregistré sous : {output_file}")
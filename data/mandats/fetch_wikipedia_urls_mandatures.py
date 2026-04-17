import pandas as pd
import requests
import time
import os


def fetch_wiki_url(qid):
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
    headers = {'User-Agent': 'MargueriteDataProject/1.0 (contact: mfresq@example.com)'}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            sitelinks = data.get("entities", {}).get(qid, {}).get("sitelinks", {})
            if "frwiki" in sitelinks:
                title = sitelinks["frwiki"]["title"]
                return f"https://fr.wikipedia.org/wiki/{title.replace(' ', '_')}"
    except Exception:
        return ""
    return ""


# --- CONFIGURATION ---
input_file = 'full_table_with_hyperlinks.xlsx'
output_file = 'full_table_final_with_mandature_wiki.xlsx'

print(f"Chargement de {input_file}...")
df = pd.read_excel(input_file)

# 1. Récupération des URLs pour les mandatures
unique_mandatures = df['mandature_wikidata_qid'].dropna().unique()
mandature_mapping = {}

print(f"Récupération des liens Wikipédia pour {len(unique_mandatures)} mandatures uniques...")
for qid in unique_mandatures:
    mandature_mapping[qid] = fetch_wiki_url(qid)
    time.sleep(0.1)

# 2. Création de la nouvelle colonne
new_col_name = 'mandature_wikipedia_url'
df[new_col_name] = df['mandature_wikidata_qid'].map(mandature_mapping)

# 3. Réorganisation pour placer la colonne à côté de mandature_wikidata_qid
cols = list(df.columns)
if 'mandature_wikidata_qid' in cols:
    idx = cols.index('mandature_wikidata_qid')
    # On déplace la nouvelle colonne juste après
    cols.insert(idx + 1, cols.pop(cols.index(new_col_name)))
    df = df[cols]

# 4. Sauvegarde avec Hyperliens
print("Génération du fichier Excel final avec hyperliens...")
with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    df.to_excel(writer, index=False, sheet_name='full_table')

    workbook = writer.book
    worksheet = writer.sheets['full_table']
    link_format = workbook.add_format({'font_color': 'blue', 'underline': 1})

    headers = list(df.columns)

    # Configuration des colonnes à transformer en liens
    link_configs = {
        'mandature_wikidata_qid': lambda x: f"https://www.wikidata.org/wiki/{x}",
        'mandature_wikipedia_url': lambda x: x,
        'person_wikidata_qid': lambda x: f"https://www.wikidata.org/wiki/{x}",
        'person_wikipedia_url': lambda x: x,
        'person_sycomore_id': lambda
            x: f"https://www2.assemblee-nationale.fr/sycomore/fiche/(num_dept)/{str(x).split('.')[0]}",
        'person_senat_id': lambda x: f"https://www.senat.fr/senateur-3eme-republique/{x}.html"
    }

    for col_name, url_func in link_configs.items():
        if col_name in headers:
            col_idx = headers.index(col_name)
            for row_idx, value in enumerate(df[col_name], start=1):
                if pd.notna(value) and str(value).strip() != "" and str(value).lower() != 'nan':
                    url = url_func(value)
                    worksheet.write_url(row_idx, col_idx, url, link_format, string=str(value))

print(f"Terminé ! Fichier disponible : {output_file}")